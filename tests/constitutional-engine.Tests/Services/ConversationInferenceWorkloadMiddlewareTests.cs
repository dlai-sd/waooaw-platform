using System.Buffers.Binary;
using System.IO.Compression;
using Google.Protobuf;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Services;
using Waooaw.WorkloadIdentity;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Services;

public sealed class ConversationInferenceWorkloadMiddlewareTests(
    InferenceWorkloadCredentialsFixture credentials
) : IClassFixture<InferenceWorkloadCredentialsFixture>
{
    [Theory]
    [InlineData("CONVERSATION_MODEL_RESERVATION", false)]
    [InlineData("CONVERSATION_MODEL_USAGE", false)]
    [InlineData("CONVERSATION_EXECUTION", true)]
    public async Task PrivateModelActionsCannotUseTheLegacyUnauthenticatedBoundary(
        string action,
        bool expectedNext
    )
    {
        var payload = new ValidateActionRequest
        {
            ActionType = action,
            ContractId = Guid.NewGuid().ToString("D"),
        }.ToByteArray();
        var frame = new byte[5 + payload.Length];
        BinaryPrimitives.WriteInt32BigEndian(frame.AsSpan(1, 4), payload.Length);
        payload.CopyTo(frame, 5);
        var http = new DefaultHttpContext();
        http.Request.Method = "POST";
        http.Request.Path = "/constitutional.v1.ConstitutionalService/ValidateAction";
        http.Request.ContentType = "application/grpc";
        http.Request.Body = new MemoryStream(frame);
        var called = false;
        var middleware = new ConversationInferenceWorkloadMiddleware(
            context =>
            {
                called = true;
                Assert.Equal(0, context.Request.Body.Position);
                return Task.CompletedTask;
            },
            NullLogger<ConversationInferenceWorkloadMiddleware>.Instance
        );
        var validator = new InferenceWorkloadValidator(
            new ConfigurationBuilder().Build(),
            TimeProvider.System
        );
        await middleware.InvokeAsync(http, validator);
        Assert.Equal(expectedNext, called);
        if (!expectedNext)
            Assert.Equal("16", http.Response.Headers["grpc-status"].ToString());
    }

    [Theory]
    [InlineData("GET", "application/grpc")]
    [InlineData("POST", "application/json")]
    [InlineData("POST", "application/grpc", "/health")]
    public async Task NonPrivateGrpcRequestsBypassInferenceBoundary(
        string method,
        string contentType,
        string path = "/constitutional.v1.ConstitutionalService/ValidateAction"
    )
    {
        var http = Context([]);
        http.Request.Method = method;
        http.Request.ContentType = contentType;
        http.Request.Path = path;
        var called = false;

        await Middleware(_ =>
            {
                called = true;
                return Task.CompletedTask;
            })
            .InvokeAsync(http, credentials.Validator());

        Assert.True(called);
    }

    [Theory]
    [InlineData("short")]
    [InlineData("negative")]
    [InlineData("trailing")]
    [InlineData("unknown-compression")]
    public async Task MalformedGrpcFramesAreRejected(string defect)
    {
        var frame =
            defect == "short"
                ? new byte[3]
                : Frame(
                    new ValidateActionRequest
                    {
                        ActionType = "CONVERSATION_MODEL_RESERVATION",
                    }.ToByteArray(),
                    compressed: defect == "unknown-compression"
                );
        if (defect == "negative")
            BinaryPrimitives.WriteInt32BigEndian(frame.AsSpan(1, 4), -1);
        if (defect == "trailing")
            frame = [.. frame, 1];
        var http = Context(frame);
        if (defect == "unknown-compression")
            http.Request.Headers["grpc-encoding"] = "brotli";

        await Middleware(_ => Task.CompletedTask)
            .InvokeAsync(
                http,
                new InferenceWorkloadValidator(
                    new ConfigurationBuilder().Build(),
                    TimeProvider.System
                )
            );

        Assert.Equal("16", http.Response.Headers["grpc-status"].ToString());
        Assert.Equal(0, http.Request.Body.Position);
    }

    [Fact]
    public async Task OversizedModelPayloadIsRejectedBeforeAuthorityValidation()
    {
        var payload = new ValidateActionRequest
        {
            ActionType = "CONVERSATION_MODEL_RESERVATION",
            ActionParameters = new string('x', 131072),
        }.ToByteArray();
        var http = Context(Frame(payload));

        await Middleware(_ => Task.CompletedTask).InvokeAsync(http, credentials.Validator());

        Assert.Equal("16", http.Response.Headers["grpc-status"].ToString());
    }

    [Theory]
    [InlineData("")]
    [InlineData("gzip")]
    [InlineData("deflate")]
    public async Task AuthenticatedModelReservationReachesService(string encoding)
    {
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        const int revision = 7;
        var payload = new ValidateActionRequest
        {
            ActionType = "CONVERSATION_MODEL_RESERVATION",
            ContractId = relationship.ToString("D"),
            DecisionSpaceVersion = revision,
            ActionParameters = $"{{\"relationship_id\":\"{relationship:D}\"}}",
        }.ToByteArray();
        var transmitted = Compress(payload, encoding);
        var http = Context(Frame(transmitted, encoding.Length > 0));
        http.Connection.ClientCertificate = credentials.Peer();
        http.Request.Headers.Authorization =
            $"Bearer {credentials.Sign(payload, tenant, relationship, revision, http.Request.Path, "ValidateAction")}";
        http.Request.Headers["x-tenant-id"] = tenant.ToString("D");
        if (encoding.Length > 0)
            http.Request.Headers["grpc-encoding"] = encoding;
        var called = false;

        await Middleware(_ =>
            {
                called = true;
                return Task.CompletedTask;
            })
            .InvokeAsync(http, credentials.Validator());

        Assert.True(called);
        Assert.Equal(0, http.Request.Body.Position);
    }

    [Fact]
    public async Task AuthenticatedModelEvidenceBindsProfessionalType()
    {
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var professional = Guid.NewGuid().ToString("D");
        const int revision = 9;
        var payload = new RecordEvidenceRequest
        {
            ActionType = "CONVERSATION_MODEL_USAGE",
            ContractId = relationship.ToString("D"),
            DecisionSpaceVersion = revision,
            ProfessionalId = professional,
        }.ToByteArray();
        var path = "/constitutional.v1.ConstitutionalService/RecordEvidence";
        var http = Context(Frame(payload), path);
        http.Connection.ClientCertificate = credentials.Peer();
        http.Request.Headers.Authorization =
            $"Bearer {credentials.Sign(payload, tenant, relationship, revision, path, "RecordEvidence", professional)}";
        http.Request.Headers["x-tenant-id"] = tenant.ToString("D");
        var called = false;

        await Middleware(_ =>
            {
                called = true;
                return Task.CompletedTask;
            })
            .InvokeAsync(http, credentials.Validator());

        Assert.True(called);
    }

    private static ConversationInferenceWorkloadMiddleware Middleware(RequestDelegate next) =>
        new(next, NullLogger<ConversationInferenceWorkloadMiddleware>.Instance);

    private static DefaultHttpContext Context(
        byte[] frame,
        string path = "/constitutional.v1.ConstitutionalService/ValidateAction"
    )
    {
        var http = new DefaultHttpContext();
        http.Request.Method = "POST";
        http.Request.Path = path;
        http.Request.ContentType = "application/grpc";
        http.Request.Body = new MemoryStream(frame);
        return http;
    }

    private static byte[] Frame(byte[] payload, bool compressed = false)
    {
        var frame = new byte[5 + payload.Length];
        frame[0] = compressed ? (byte)1 : (byte)0;
        BinaryPrimitives.WriteInt32BigEndian(frame.AsSpan(1, 4), payload.Length);
        payload.CopyTo(frame, 5);
        return frame;
    }

    private static byte[] Compress(byte[] payload, string encoding)
    {
        if (encoding.Length == 0)
            return payload;
        using var output = new MemoryStream();
        using (
            Stream compressor =
                encoding == "gzip"
                    ? new GZipStream(output, CompressionMode.Compress, leaveOpen: true)
                    : new DeflateStream(output, CompressionMode.Compress, leaveOpen: true)
        )
            compressor.Write(payload);
        return output.ToArray();
    }
}
