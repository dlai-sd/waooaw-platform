// Implements: work-contracts/WC-062-wc034-f6-voice-interaction.md WC062-03, WC062-05
// constitutional_basis: C-005, C-007, C-023, C-026, C-042, C-049, C-059, C-063, C-076

using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Buffers.Binary;
using Microsoft.Extensions.Configuration;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Voice;

public sealed class ConfiguredVoiceMediaGatewayTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), $"waooaw-media-test-{Guid.NewGuid():N}");
    private readonly string _probe = Path.Combine(Path.GetTempPath(), $"waooaw-ffprobe-{Guid.NewGuid():N}");

    [Fact]
    public async Task ValidMediaIsScannedEncryptedRetainedPurgedAndErasable()
    {
        WriteProbe(0, "{\"streams\":[{\"codec_name\":\"opus\"}],\"format\":{\"format_name\":\"matroska,webm\",\"duration\":\"12.500\"}}");
        await using var clam = new ClamServer("stream: OK\0", 2);
        var gateway = Gateway(clam.Port);
        var plaintext = Encoding.UTF8.GetBytes("not-a-real-container-but-probe-is-controlled");

        var first = await gateway.ValidateScanAndStoreAsync(
            new MemoryStream(plaintext), "audio/webm", Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None);
        Assert.Equal("audio/webm", first.DetectedMediaType);
        Assert.Equal(12_500, first.DurationMilliseconds);
        Assert.Matches("^[0-9a-f]{64}$", first.ContentSha256);
        Assert.True(Guid.TryParseExact(first.PayloadReference, "N", out _));
        var path = Path.Combine(_root, $"{first.PayloadReference}.voice");
        Assert.True(File.Exists(path));
        Assert.DoesNotContain("not-a-real-container", Encoding.UTF8.GetString(await File.ReadAllBytesAsync(path)));

        var retention = DateTimeOffset.UtcNow.AddDays(30);
        await gateway.SetRetentionAsync(first.PayloadReference, retention, CancellationToken.None);
        Assert.InRange(File.GetLastWriteTimeUtc(path), retention.UtcDateTime.AddSeconds(-2), retention.UtcDateTime.AddSeconds(2));
        await gateway.PurgeExpiredAsync(retention.AddSeconds(-1), CancellationToken.None);
        Assert.True(File.Exists(path));
        await gateway.PurgeExpiredAsync(retention.AddSeconds(1), CancellationToken.None);
        Assert.False(File.Exists(path));

        var second = await gateway.ValidateScanAndStoreAsync(
            new MemoryStream(plaintext), "audio/webm", Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None);
        await gateway.EraseAsync(second.PayloadReference, CancellationToken.None);
        Assert.False(File.Exists(Path.Combine(_root, $"{second.PayloadReference}.voice")));
    }

    [Fact]
    public async Task RejectsUnsupportedEmptyAndOversizedMediaBeforeExternalDispatch()
    {
        var gateway = Gateway(1);
        await Assert.ThrowsAsync<VoiceInvalidMediaException>(() => gateway.ValidateScanAndStoreAsync(
            new MemoryStream([1]), "audio/mpeg", Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None));
        await Assert.ThrowsAsync<VoiceInvalidMediaException>(() => gateway.ValidateScanAndStoreAsync(
            new MemoryStream(), "audio/webm", Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None));
        await Assert.ThrowsAsync<VoiceLimitExceededException>(() => gateway.ValidateScanAndStoreAsync(
            new MemoryStream(new byte[15 * 1024 * 1024 + 1]), "audio/webm",
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None));
    }

    [Fact]
    public async Task MalwareAndUnavailableScannerFailClosedWithoutStorage()
    {
        WriteProbe(0, "{\"streams\":[{\"codec_name\":\"opus\"}],\"format\":{\"format_name\":\"ogg\",\"duration\":\"1.000\"}}");
        await using (var clam = new ClamServer("stream: Eicar-Test-Signature FOUND\0", 1))
        {
            await Assert.ThrowsAsync<VoiceBlockedException>(() => Gateway(clam.Port).ValidateScanAndStoreAsync(
                new MemoryStream([1, 2, 3]), "audio/ogg", Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None));
        }
        await Assert.ThrowsAsync<VoiceUnavailableException>(() => Gateway(1).ValidateScanAndStoreAsync(
            new MemoryStream([1, 2, 3]), "audio/ogg", Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None));
        Assert.False(Directory.Exists(_root));
    }

    [Fact]
    public async Task ProbeMismatchInvalidReferenceAndMissingConfigurationFailClosed()
    {
        WriteProbe(0, "{\"streams\":[{\"codec_name\":\"mp3\"}],\"format\":{\"format_name\":\"mp3\",\"duration\":\"1.000\"}}");
        await Assert.ThrowsAsync<VoiceInvalidMediaException>(() => Gateway(1).ValidateScanAndStoreAsync(
            new MemoryStream([1]), "audio/webm", Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None));
        var gateway = Gateway(1);
        await Assert.ThrowsAsync<VoiceUnavailableException>(() => gateway.EraseAsync("../payload", CancellationToken.None));
        await Assert.ThrowsAsync<VoiceUnavailableException>(() => gateway.SetRetentionAsync(Guid.NewGuid().ToString("N"), DateTimeOffset.UtcNow, CancellationToken.None));
        Assert.Throws<InvalidOperationException>(() => new ConfiguredVoiceMediaGateway(new ConfigurationBuilder().Build()));
    }

    [Fact]
    public void TranscriptProtectorUsesAuthenticatedCiphertext()
    {
        var configuration = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["Voice:ContentEncryptionKey"] = Convert.ToBase64String(Enumerable.Range(33, 32).Select(value => (byte)value).ToArray()),
        }).Build();
        var protector = new AesVoiceContentProtector(configuration);
        var ciphertext = protector.Protect("sensitive transcript");

        Assert.DoesNotContain("sensitive transcript", ciphertext);
        Assert.Equal("sensitive transcript", protector.Unprotect(ciphertext));
        Assert.Throws<CryptographicException>(() => protector.Unprotect(Convert.ToBase64String(new byte[28])));
    }

    private ConfiguredVoiceMediaGateway Gateway(int port) => new(new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
    {
        ["Voice:Media:FfprobePath"] = _probe,
        ["Voice:Media:ClamAvHost"] = "127.0.0.1",
        ["Voice:Media:ClamAvPort"] = port.ToString(),
        ["Voice:Media:PayloadRoot"] = _root,
        ["Voice:Media:EncryptionKey"] = Convert.ToBase64String(Enumerable.Range(1, 32).Select(value => (byte)value).ToArray()),
    }).Build());

    private void WriteProbe(int exitCode, string output)
    {
        File.WriteAllText(_probe, $"#!/bin/sh\nprintf '%s' '{output}'\nexit {exitCode}\n");
        if (!OperatingSystem.IsWindows())
        {
            File.SetUnixFileMode(_probe, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        }
    }

    public void Dispose()
    {
        if (Directory.Exists(_root)) Directory.Delete(_root, true);
        if (File.Exists(_probe)) File.Delete(_probe);
    }

    private sealed class ClamServer : IAsyncDisposable
    {
        private readonly TcpListener _listener = new(IPAddress.Loopback, 0);
        private readonly CancellationTokenSource _stopping = new();
        private readonly Task _server;
        public int Port { get; }

        public ClamServer(string response, int connections)
        {
            _listener.Start();
            Port = ((IPEndPoint)_listener.LocalEndpoint).Port;
            _server = ServeAsync(response, connections);
        }

        private async Task ServeAsync(string response, int connections)
        {
            for (var index = 0; index < connections; index++)
            {
                using var client = await _listener.AcceptTcpClientAsync(_stopping.Token);
                await using var stream = client.GetStream();
                var command = new byte["zINSTREAM\0"u8.Length];
                await stream.ReadExactlyAsync(command, _stopping.Token);
                Assert.Equal("zINSTREAM\0"u8.ToArray(), command);
                var lengthBytes = new byte[sizeof(int)];
                while (true)
                {
                    await stream.ReadExactlyAsync(lengthBytes, _stopping.Token);
                    var length = BinaryPrimitives.ReadInt32BigEndian(lengthBytes);
                    if (length == 0) break;
                    var chunk = new byte[length];
                    await stream.ReadExactlyAsync(chunk, _stopping.Token);
                }
                await stream.WriteAsync(Encoding.UTF8.GetBytes(response), _stopping.Token);
            }
        }

        public async ValueTask DisposeAsync()
        {
            _stopping.Cancel();
            _listener.Stop();
            try { await _server; } catch (OperationCanceledException) { }
            _stopping.Dispose();
        }
    }
}
