// Implements: architecture/reference/security/wc062-voice-security-contract.md controls 3-5
// constitutional_basis: C-005, C-007, C-023, C-026, C-042, C-049, C-059, C-063

using System.Diagnostics;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services;

public sealed class ConfiguredVoiceMediaGateway(IConfiguration configuration) : IVoiceMediaGateway
{
    private const int MaximumBytes = 15 * 1024 * 1024;
    private static readonly HashSet<string> AllowedTypes = ["audio/webm", "audio/ogg", "audio/wav"];
    private readonly string _ffprobePath = Required(configuration, "Voice:Media:FfprobePath");
    private readonly string _clamAvHost = Required(configuration, "Voice:Media:ClamAvHost");
    private readonly int _clamAvPort = configuration.GetValue("Voice:Media:ClamAvPort", 3310);
    private readonly string _payloadRoot = Required(configuration, "Voice:Media:PayloadRoot");
    private readonly byte[] _key = ReadKey(configuration);

    public async Task<VoiceMediaInspection> ValidateScanAndStoreAsync(
        Stream audio,
        string declaredMediaType,
        Guid tenantId,
        Guid relationshipId,
        Guid sessionId,
        CancellationToken cancellationToken)
    {
        if (!AllowedTypes.Contains(declaredMediaType)) throw new VoiceInvalidMediaException("invalid_media");
        await using var buffer = new MemoryStream();
        await CopyBoundedAsync(audio, buffer, cancellationToken);
        var bytes = buffer.ToArray();
        var probe = await InspectAsync(bytes, cancellationToken);
        if (!AllowedTypes.Contains(probe.MediaType)
            || !string.Equals(probe.MediaType, declaredMediaType, StringComparison.Ordinal)
            || probe.DurationMilliseconds is < 1 or > 180_000)
        {
            throw new VoiceInvalidMediaException("invalid_media");
        }

        await ScanAsync(bytes, cancellationToken);
        Directory.CreateDirectory(_payloadRoot);
        var payloadReference = Guid.NewGuid().ToString("N");
        var path = PayloadPath(payloadReference);
        var nonce = RandomNumberGenerator.GetBytes(12);
        var tag = new byte[16];
        var ciphertext = new byte[bytes.Length];
        using (var aes = new AesGcm(_key, tag.Length))
        {
            aes.Encrypt(nonce, bytes, ciphertext, tag, Binding(tenantId, relationshipId, sessionId));
        }
        await File.WriteAllBytesAsync(path, nonce.Concat(tag).Concat(ciphertext).ToArray(), cancellationToken);
        File.SetLastWriteTimeUtc(path, DateTime.UtcNow.AddHours(24));
        return new(
            Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant(),
            declaredMediaType,
            probe.MediaType,
            bytes.LongLength,
            probe.DurationMilliseconds,
            payloadReference);
    }

    public Task EraseAsync(string payloadReference, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!Guid.TryParseExact(payloadReference, "N", out _)) throw new VoiceUnavailableException();
        var path = PayloadPath(payloadReference);
        if (File.Exists(path)) File.Delete(path);
        return Task.CompletedTask;
    }

    public Task SetRetentionAsync(string payloadReference, DateTimeOffset retainUntil, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!Guid.TryParseExact(payloadReference, "N", out _)) throw new VoiceUnavailableException();
        var path = PayloadPath(payloadReference);
        if (!File.Exists(path)) throw new VoiceUnavailableException();
        File.SetLastWriteTimeUtc(path, retainUntil.UtcDateTime);
        return Task.CompletedTask;
    }

    public Task PurgeExpiredAsync(DateTimeOffset now, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!Directory.Exists(_payloadRoot)) return Task.CompletedTask;
        foreach (var path in Directory.EnumerateFiles(_payloadRoot, "*.voice"))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (File.GetLastWriteTimeUtc(path) <= now.UtcDateTime) File.Delete(path);
        }
        return Task.CompletedTask;
    }

    private async Task<MediaProbe> InspectAsync(byte[] bytes, CancellationToken cancellationToken)
    {
        var temporaryPath = Path.Combine(Path.GetTempPath(), $"waooaw-voice-{Guid.NewGuid():N}");
        try
        {
            await File.WriteAllBytesAsync(temporaryPath, bytes, cancellationToken);
            using var process = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = _ffprobePath,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                },
            };
            process.StartInfo.ArgumentList.Add("-v");
            process.StartInfo.ArgumentList.Add("error");
            process.StartInfo.ArgumentList.Add("-select_streams");
            process.StartInfo.ArgumentList.Add("a:0");
            process.StartInfo.ArgumentList.Add("-show_entries");
            process.StartInfo.ArgumentList.Add("format=format_name,duration:stream=codec_name");
            process.StartInfo.ArgumentList.Add("-of");
            process.StartInfo.ArgumentList.Add("json");
            process.StartInfo.ArgumentList.Add(temporaryPath);
            if (!process.Start()) throw new VoiceUnavailableException();
            var output = await process.StandardOutput.ReadToEndAsync(cancellationToken);
            await process.WaitForExitAsync(cancellationToken);
            if (process.ExitCode != 0) throw new VoiceInvalidMediaException("invalid_media");
            using var document = JsonDocument.Parse(output);
            var format = document.RootElement.GetProperty("format");
            var formatName = format.GetProperty("format_name").GetString() ?? string.Empty;
            var codec = document.RootElement.GetProperty("streams")[0].GetProperty("codec_name").GetString() ?? string.Empty;
            if (!decimal.TryParse(format.GetProperty("duration").GetString(), System.Globalization.NumberStyles.Number,
                    System.Globalization.CultureInfo.InvariantCulture, out var seconds))
            {
                throw new VoiceInvalidMediaException("invalid_media");
            }
            var mediaType = (formatName, codec) switch
            {
                (var name, "opus") when name.Contains("webm", StringComparison.Ordinal) => "audio/webm",
                (var name, "opus") when name.Contains("ogg", StringComparison.Ordinal) => "audio/ogg",
                (var name, "pcm_s16le" or "pcm_s24le" or "pcm_s32le") when name.Contains("wav", StringComparison.Ordinal) => "audio/wav",
                _ => throw new VoiceInvalidMediaException("invalid_media"),
            };
            return new(mediaType, checked((int)(seconds * 1000)));
        }
        catch (VoiceInvalidMediaException) { throw; }
        catch (OperationCanceledException) { throw; }
        catch { throw new VoiceUnavailableException(); }
        finally
        {
            if (File.Exists(temporaryPath)) File.Delete(temporaryPath);
        }
    }

    private async Task ScanAsync(byte[] bytes, CancellationToken cancellationToken)
    {
        try
        {
            using var client = new TcpClient();
            await client.ConnectAsync(_clamAvHost, _clamAvPort, cancellationToken);
            await using var stream = client.GetStream();
            await stream.WriteAsync("zINSTREAM\0"u8.ToArray(), cancellationToken);
            var length = BitConverter.GetBytes(System.Net.IPAddress.HostToNetworkOrder(bytes.Length));
            await stream.WriteAsync(length, cancellationToken);
            await stream.WriteAsync(bytes, cancellationToken);
            await stream.WriteAsync(new byte[4], cancellationToken);
            using var reader = new StreamReader(stream, Encoding.UTF8, leaveOpen: true);
            var result = await reader.ReadToEndAsync(cancellationToken);
            if (result.Contains("FOUND", StringComparison.Ordinal)) throw new VoiceBlockedException("quarantined");
            if (!result.Contains("OK", StringComparison.Ordinal)) throw new VoiceUnavailableException();
        }
        catch (VoiceBlockedException) { throw; }
        catch (OperationCanceledException) { throw; }
        catch { throw new VoiceUnavailableException(); }
    }

    private static async Task CopyBoundedAsync(Stream source, Stream destination, CancellationToken cancellationToken)
    {
        var buffer = new byte[81920];
        var total = 0;
        int read;
        while ((read = await source.ReadAsync(buffer, cancellationToken)) > 0)
        {
            total += read;
            if (total > MaximumBytes) throw new VoiceLimitExceededException("limit_exceeded");
            await destination.WriteAsync(buffer.AsMemory(0, read), cancellationToken);
        }
        if (total == 0) throw new VoiceInvalidMediaException("invalid_media");
    }

    private string PayloadPath(string payloadReference) => Path.Combine(_payloadRoot, $"{payloadReference}.voice");
    private static byte[] Binding(Guid tenantId, Guid relationshipId, Guid sessionId) =>
        Encoding.UTF8.GetBytes($"{tenantId:N}:{relationshipId:N}:{sessionId:N}");
    private static string Required(IConfiguration configuration, string name) =>
        !string.IsNullOrWhiteSpace(configuration[name]) ? configuration[name]! : throw new InvalidOperationException($"{name} is required.");
    private static byte[] ReadKey(IConfiguration configuration)
    {
        var key = Convert.FromBase64String(Required(configuration, "Voice:Media:EncryptionKey"));
        return key.Length == 32 ? key : throw new InvalidOperationException("Voice media key must be 256 bits.");
    }

    private sealed record MediaProbe(string MediaType, int DurationMilliseconds);
}

public sealed class VoiceMediaRetentionWorker(ConfiguredVoiceMediaGateway gateway) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromMinutes(15));
        do
        {
            await gateway.PurgeExpiredAsync(DateTimeOffset.UtcNow, stoppingToken);
        } while (await timer.WaitForNextTickAsync(stoppingToken));
    }
}