using System.Buffers.Binary;
using Google.Protobuf;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Services;
using Waooaw.WorkloadIdentity;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Services;

public sealed class ConversationInferenceWorkloadMiddlewareTests
{
    [Theory]
    [InlineData("CONVERSATION_MODEL_RESERVATION", false)]
    [InlineData("CONVERSATION_MODEL_USAGE", false)]
    [InlineData("CONVERSATION_EXECUTION", true)]
    public async Task PrivateModelActionsCannotUseTheLegacyUnauthenticatedBoundary(string action, bool expectedNext)
    {
        var payload = new ValidateActionRequest { ActionType = action, ContractId = Guid.NewGuid().ToString("D") }.ToByteArray();
        var frame = new byte[5 + payload.Length];
        BinaryPrimitives.WriteInt32BigEndian(frame.AsSpan(1, 4), payload.Length);
        payload.CopyTo(frame, 5);
        var http = new DefaultHttpContext();
        http.Request.Method = "POST";
        http.Request.Path = "/constitutional.v1.ConstitutionalService/ValidateAction";
        http.Request.ContentType = "application/grpc";
        http.Request.Body = new MemoryStream(frame);
        var called = false;
        var middleware = new ConversationInferenceWorkloadMiddleware(context =>
        {
            called = true;
            Assert.Equal(0, context.Request.Body.Position);
            return Task.CompletedTask;
        }, NullLogger<ConversationInferenceWorkloadMiddleware>.Instance);
        var validator = new InferenceWorkloadValidator(new ConfigurationBuilder().Build(), TimeProvider.System);
        await middleware.InvokeAsync(http, validator);
        Assert.Equal(expectedNext, called);
        if (!expectedNext)
            Assert.Equal("16", http.Response.Headers["grpc-status"].ToString());
    }
}
