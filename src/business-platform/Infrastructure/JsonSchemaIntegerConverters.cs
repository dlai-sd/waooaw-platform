using System.Text.Json;
using System.Text.Json.Serialization;

namespace Waooaw.BusinessPlatform.Infrastructure;

public sealed class JsonSchemaInt32Converter : JsonConverter<int>
{
    public override int Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        if (
            reader.TokenType != JsonTokenType.Number
            || !reader.TryGetDecimal(out var value)
            || value != decimal.Truncate(value)
            || value < int.MinValue
            || value > int.MaxValue
        )
            throw new JsonException("Expected a 32-bit integer value.");

        return decimal.ToInt32(value);
    }

    public override void Write(Utf8JsonWriter writer, int value, JsonSerializerOptions options) =>
        writer.WriteNumberValue(value);
}

public sealed class JsonSchemaInt64Converter : JsonConverter<long>
{
    public override long Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        if (
            reader.TokenType != JsonTokenType.Number
            || !reader.TryGetDecimal(out var value)
            || value != decimal.Truncate(value)
            || value < long.MinValue
            || value > long.MaxValue
        )
            throw new JsonException("Expected a 64-bit integer value.");

        return decimal.ToInt64(value);
    }

    public override void Write(Utf8JsonWriter writer, long value, JsonSerializerOptions options) =>
        writer.WriteNumberValue(value);
}
