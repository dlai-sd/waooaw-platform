// Implements: WC-134 R006/R008; authenticated CE inference decisions and evidence.
using System.Buffers.Binary;
using System.IO.Compression;
using System.Security.Cryptography;
using Google.Protobuf;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.WorkloadIdentity;

namespace Waooaw.ConstitutionalEngine.Services;

public sealed class ConversationInferenceWorkloadMiddleware(
    RequestDelegate next,
    ILogger<ConversationInferenceWorkloadMiddleware> logger
)
{
    private const int MaximumGrpcMessage = 4 * 1024 * 1024;

    public async Task InvokeAsync(HttpContext http, InferenceWorkloadValidator validator)
    {
        var path = http.Request.Path.Value;
        if (
            path
                is not (
                    "/constitutional.v1.ConstitutionalService/ValidateAction"
                    or "/constitutional.v1.ConstitutionalService/RecordEvidence"
                )
            || http.Request.Method != "POST"
            || http.Request.ContentType?.StartsWith("application/grpc", StringComparison.Ordinal)
                != true
        )
        {
            await next(http);
            return;
        }
        http.Request.EnableBuffering(bufferLimit: MaximumGrpcMessage + 5L);
        try
        {
            var header = new byte[5];
            await http.Request.Body.ReadExactlyAsync(header, http.RequestAborted);
            var length = BinaryPrimitives.ReadInt32BigEndian(header.AsSpan(1));
            if (length < 0 || length > MaximumGrpcMessage || header[0] > 1)
                throw new InferenceWorkloadRejectedException();
            var bytes = new byte[length];
            await http.Request.Body.ReadExactlyAsync(bytes, http.RequestAborted);
            if (await http.Request.Body.ReadAsync(new byte[1], http.RequestAborted) != 0)
                throw new InferenceWorkloadRejectedException();
            if (header[0] == 1)
                bytes = await DecompressAsync(
                    bytes,
                    http.Request.Headers["grpc-encoding"].ToString(),
                    http.RequestAborted
                );
            string action,
                contract,
                professional = "";
            int revision;
            if (path.EndsWith("/ValidateAction", StringComparison.Ordinal))
            {
                var request = ValidateActionRequest.Parser.ParseFrom(bytes);
                action = request.ActionType;
                contract = request.ContractId;
                revision = request.DecisionSpaceVersion;
            }
            else
            {
                var request = RecordEvidenceRequest.Parser.ParseFrom(bytes);
                action = request.ActionType;
                contract = request.ContractId;
                revision = request.DecisionSpaceVersion;
                professional = request.ProfessionalId;
            }
            if (action.StartsWith("CONVERSATION_MODEL_", StringComparison.Ordinal))
            {
                if (bytes.Length > 131072)
                    throw new InferenceWorkloadRejectedException();
                var operation = path.Split('/')[^1];
                var caller = await validator.RequireAsync(
                    http,
                    "business-platform",
                    "constitutional-engine",
                    "CONVERSATION_INFERENCE_EVIDENCE",
                    path,
                    operation,
                    Convert.ToHexStringLower(SHA256.HashData(bytes)),
                    http.RequestAborted
                );
                if (
                    contract != caller.RelationshipId.ToString("D")
                    || http.Request.Headers["x-tenant-id"].ToString()
                        != caller.TenantId.ToString("D")
                    || !caller.ExpectedVersions.TryGetValue(
                        "decisionSpaceRevision",
                        out var expectedRevision
                    )
                    || expectedRevision
                        != revision.ToString(System.Globalization.CultureInfo.InvariantCulture)
                    || !caller.ExpectedVersions.ContainsKey("mandateDigest")
                    || professional.Length > 0
                        && (
                            !caller.ExpectedVersions.TryGetValue(
                                "professionalType",
                                out var expectedProfessional
                            )
                            || professional != expectedProfessional
                        )
                )
                    throw new InferenceWorkloadRejectedException();
            }
        }
        catch (Exception error)
            when (error
                    is InferenceWorkloadRejectedException
                        or InvalidProtocolBufferException
                        or IOException
            )
        {
            logger.LogWarning(
                "CE inference boundary rejected {Route}: {Error}",
                path,
                error.GetType().Name
            );
            http.Response.StatusCode = 200;
            http.Response.ContentType = "application/grpc";
            http.Response.Headers["grpc-status"] = "16";
            http.Response.Headers["grpc-message"] = "Inference workload authority denied";
            return;
        }
        finally
        {
            http.Request.Body.Position = 0;
        }
        await next(http);
    }

    private static async Task<byte[]> DecompressAsync(
        byte[] bytes,
        string encoding,
        CancellationToken ct
    )
    {
        using var input = new MemoryStream(bytes);
        using Stream decoder = encoding switch
        {
            "gzip" => new GZipStream(input, CompressionMode.Decompress),
            "deflate" => new DeflateStream(input, CompressionMode.Decompress),
            _ => throw new InferenceWorkloadRejectedException(),
        };
        using var output = new MemoryStream();
        var buffer = new byte[8192];
        int read;
        while ((read = await decoder.ReadAsync(buffer, ct)) > 0)
        {
            if (output.Length + read > MaximumGrpcMessage)
                throw new InferenceWorkloadRejectedException();
            output.Write(buffer, 0, read);
        }
        return output.ToArray();
    }
}
