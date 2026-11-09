using System.Text.Json;
using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Infrastructure;

public sealed class JsonSchemaIntegerConverterTests
{
    [Theory]
    [InlineData("1.0", 1)]
    [InlineData("-2147483648", int.MinValue)]
    [InlineData("2147483647", int.MaxValue)]
    public void Int32ConverterAcceptsJsonSchemaIntegersAndWritesCanonicalNumbers(
        string json,
        int expected
    )
    {
        var options = new JsonSerializerOptions();
        options.Converters.Add(new JsonSchemaInt32Converter());

        Assert.Equal(expected, JsonSerializer.Deserialize<int>(json, options));
        Assert.Equal(
            expected,
            JsonSerializer.Deserialize<int>(JsonSerializer.Serialize(expected, options), options)
        );
    }

    [Theory]
    [InlineData("true")]
    [InlineData("1.5")]
    [InlineData("2147483648")]
    [InlineData("1e500")]
    public void Int32ConverterRejectsNonIntegersAndOutOfRangeNumbers(string json)
    {
        var options = new JsonSerializerOptions();
        options.Converters.Add(new JsonSchemaInt32Converter());

        Assert.Throws<JsonException>(() => JsonSerializer.Deserialize<int>(json, options));
    }

    [Theory]
    [InlineData("61093.0", 61093L)]
    [InlineData("-9223372036854775808", long.MinValue)]
    [InlineData("9223372036854775807", long.MaxValue)]
    public void Int64ConverterAcceptsJsonSchemaIntegersAndWritesCanonicalNumbers(
        string json,
        long expected
    )
    {
        var options = new JsonSerializerOptions();
        options.Converters.Add(new JsonSchemaInt64Converter());

        Assert.Equal(expected, JsonSerializer.Deserialize<long>(json, options));
        Assert.Equal(
            expected,
            JsonSerializer.Deserialize<long>(JsonSerializer.Serialize(expected, options), options)
        );
    }

    [Theory]
    [InlineData("false")]
    [InlineData("-2.25")]
    [InlineData("9223372036854775808")]
    [InlineData("-1e500")]
    public void Int64ConverterRejectsNonIntegersAndOutOfRangeNumbers(string json)
    {
        var options = new JsonSerializerOptions();
        options.Converters.Add(new JsonSchemaInt64Converter());

        Assert.Throws<JsonException>(() => JsonSerializer.Deserialize<long>(json, options));
    }
}
