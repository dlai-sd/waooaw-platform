using System.Reflection;
using System.Text.Json;
using Waooaw.BusinessPlatform.Controllers;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ControllerContractRecordTests
{
    [Fact]
    public void PublicControllerRecords_AreSerializableValueContracts()
    {
        var contractTypes = typeof(IdentityController)
            .Assembly.GetTypes()
            .Where(type =>
                type.IsPublic
                && !type.ContainsGenericParameters
                && type.Namespace
                    is "Waooaw.BusinessPlatform.Controllers"
                        or "Waooaw.BusinessPlatform.Services"
                && type.GetConstructors().Length > 0
                && type.GetProperty(
                    "EqualityContract",
                    BindingFlags.Instance | BindingFlags.NonPublic
                )
                    is not null
            )
            .OrderBy(type => type.FullName)
            .ToArray();

        Assert.NotEmpty(contractTypes);
        foreach (var contractType in contractTypes)
        {
            var constructor = contractType
                .GetConstructors()
                .OrderByDescending(candidate => candidate.GetParameters().Length)
                .First();
            var arguments = constructor
                .GetParameters()
                .Select(parameter => ContractValue(parameter.ParameterType))
                .ToArray();
            var first = constructor.Invoke(arguments);
            var second = constructor.Invoke(arguments);

            Assert.Equal(first, second);
            Assert.False(first.Equals(new object()));
            Assert.Equal(first.GetHashCode(), second.GetHashCode());
            Assert.NotEmpty(first.ToString()!);
            Assert.NotEmpty(JsonSerializer.Serialize(first, contractType));
        }
    }

    private static object? ContractValue(Type type)
    {
        var nullable = Nullable.GetUnderlyingType(type);
        if (nullable is not null)
            return null;
        if (type == typeof(string))
            return "contract-value";
        if (type == typeof(Guid))
            return Guid.Parse("10000000-0000-4000-8000-000000000001");
        if (type == typeof(DateTimeOffset))
            return DateTimeOffset.UnixEpoch;
        if (type == typeof(DateTime))
            return DateTime.UnixEpoch;
        if (type == typeof(JsonElement))
            return JsonSerializer.SerializeToElement(new { value = "contract-value" });
        if (type.IsEnum)
            return Enum.GetValues(type).GetValue(0);
        if (type.IsArray)
            return Array.CreateInstance(type.GetElementType()!, 0);
        if (type.IsGenericType)
        {
            var definition = type.GetGenericTypeDefinition();
            var arguments = type.GetGenericArguments();
            if (
                definition == typeof(IReadOnlyList<>)
                || definition == typeof(IEnumerable<>)
                || definition == typeof(ICollection<>)
                || definition == typeof(IList<>)
            )
                return Activator.CreateInstance(typeof(List<>).MakeGenericType(arguments));
            if (
                definition == typeof(IReadOnlyDictionary<,>)
                || definition == typeof(IDictionary<,>)
            )
                return Activator.CreateInstance(typeof(Dictionary<,>).MakeGenericType(arguments));
        }
        if (type.IsValueType)
            return Activator.CreateInstance(type);

        var constructor = type.GetConstructors()
            .OrderByDescending(candidate => candidate.GetParameters().Length)
            .FirstOrDefault();
        if (constructor is null)
            return null;
        return constructor.Invoke(
            constructor
                .GetParameters()
                .Select(parameter => ContractValue(parameter.ParameterType))
                .ToArray()
        );
    }
}
