# Canonical Patterns — WC-013 (dotnet)

**Status:** CANDIDATE — awaiting Constitutional Analyst review  

**Source sprint:** WC-013  

**Extracted:** 2026-07-29  

**Confidence:** 0.5 (CANDIDATE) — promoted to 1.0 after CA review


---

### DOTNET-TEST-WC013-CCT_MT01_TenantIsolationTests.cs

**Status:** CANDIDATE  
**Category:** test-structure  
**Confidence:** 0.5  
**Source:** `tests/business-platform.Tests/Infrastructure/CCT_MT01_TenantIsolationTests.cs` (from GOAL-WC013)  
**Created:** 2026-07-29

xUnit test structure from WC-013: AAA pattern with FluentAssertions.

```
[Fact]
public async Task Method_Scenario_ExpectedResult()
{
    // Arrange
    var sut = new SomeClass(Mock.Of<IDep>());

    // Act
    var result = await sut.DoSomethingAsync();

    // Assert
    result.Should().NotBeNull();
    result.SomeProperty.Should().Be(expectedValue);
}
```


---

### DOTNET-ANNO-WC013-C041ToolAuthorizationEvaluator.cs

**Status:** CANDIDATE  
**Category:** annotations  
**Confidence:** 0.5  
**Source:** `src/constitutional-engine/Evaluators/C041ToolAuthorizationEvaluator.cs` (from GOAL-WC013)  
**Created:** 2026-07-29

Constitutional annotation pattern confirmed in WC-013 (C-059 + C-073).

```
// Implements: architecture/reference/components/{service}.md §{Section}
// Constitutional basis: C-NNN ({Claim Name})
```


---

### DOTNET-ANNO-WC013-C043BudgetCeilingEvaluator.cs

**Status:** CANDIDATE  
**Category:** annotations  
**Confidence:** 0.5  
**Source:** `src/constitutional-engine/Evaluators/C043BudgetCeilingEvaluator.cs` (from GOAL-WC013)  
**Created:** 2026-07-29

Constitutional annotation pattern confirmed in WC-013 (C-059 + C-073).

```
// Implements: architecture/reference/components/{service}.md §{Section}
// Constitutional basis: C-NNN ({Claim Name})
```


---

### DOTNET-ANNO-WC013-C048NonExploitationEvaluator.cs

**Status:** CANDIDATE  
**Category:** annotations  
**Confidence:** 0.5  
**Source:** `src/constitutional-engine/Evaluators/C048NonExploitationEvaluator.cs` (from GOAL-WC013)  
**Created:** 2026-07-29

Constitutional annotation pattern confirmed in WC-013 (C-059 + C-073).

```
// Implements: architecture/reference/components/{service}.md §{Section}
// Constitutional basis: C-NNN ({Claim Name})
```


---

### DOTNET-ANNO-WC013-C049HonestLimitationEvaluator.cs

**Status:** CANDIDATE  
**Category:** annotations  
**Confidence:** 0.5  
**Source:** `src/constitutional-engine/Evaluators/C049HonestLimitationEvaluator.cs` (from GOAL-WC013)  
**Created:** 2026-07-29

Constitutional annotation pattern confirmed in WC-013 (C-059 + C-073).

```
// Implements: architecture/reference/components/{service}.md §{Section}
// Constitutional basis: C-NNN ({Claim Name})
```


---

### DOTNET-ANNO-WC013-C062AiSecurityEvaluator.cs

**Status:** CANDIDATE  
**Category:** annotations  
**Confidence:** 0.5  
**Source:** `src/constitutional-engine/Evaluators/C062AiSecurityEvaluator.cs` (from GOAL-WC013)  
**Created:** 2026-07-29

Constitutional annotation pattern confirmed in WC-013 (C-059 + C-073).

```
// Implements: architecture/reference/components/{service}.md §{Section}
// Constitutional basis: C-NNN ({Claim Name})
```


---

### DOTNET-GRPC-WC013-RecordEvidence

**Status:** CANDIDATE  
**Category:** grpc-service  
**Confidence:** 0.5  
**Source:** `src/constitutional-engine/Services/ConstitutionalEngineService.cs` (from GOAL-WC013)  
**Created:** 2026-07-29

gRPC service method pattern from WC-013: async override with proper cancellation.

```
public override async Task<RecordEvidenceResponse> RecordEvidence(
    RecordEvidenceRequest request, ServerCallContext context)
{
    // 1. Validate (CE.ValidateAction if needed)
    // 2. Record evidence BEFORE returning (C-023)
    // 3. Execute business logic
    return new RecordEvidenceResponse { /* ... */ };
}
```


---

### DOTNET-ANNO-WC013-CCT_HO01_EmergencyStopLatencyTests.cs

**Status:** CANDIDATE  
**Category:** annotations  
**Confidence:** 0.5  
**Source:** `tests/constitutional-engine.Tests/EmergencyStop/CCT_HO01_EmergencyStopLatencyTests.cs` (from GOAL-WC013)  
**Created:** 2026-07-29

Constitutional annotation pattern confirmed in WC-013 (C-059 + C-073).

```
// Implements: architecture/reference/components/{service}.md §{Section}
// Constitutional basis: C-NNN ({Claim Name})
```


---

### DOTNET-TEST-WC013-CCT_HO01_EmergencyStopLatencyTests.cs

**Status:** CANDIDATE  
**Category:** test-structure  
**Confidence:** 0.5  
**Source:** `tests/constitutional-engine.Tests/EmergencyStop/CCT_HO01_EmergencyStopLatencyTests.cs` (from GOAL-WC013)  
**Created:** 2026-07-29

xUnit test structure from WC-013: AAA pattern with FluentAssertions.

```
[Fact]
public async Task Method_Scenario_ExpectedResult()
{
    // Arrange
    var sut = new SomeClass(Mock.Of<IDep>());

    // Act
    var result = await sut.DoSomethingAsync();

    // Assert
    result.Should().NotBeNull();
    result.SomeProperty.Should().Be(expectedValue);
}
```


---

### DOTNET-TEST-WC013-CCT_EF01_C041ToolAuthorizationEvaluatorTests.cs

**Status:** CANDIDATE  
**Category:** test-structure  
**Confidence:** 0.5  
**Source:** `tests/constitutional-engine.Tests/Evaluators/CCT_EF01_C041ToolAuthorizationEvaluatorTests.cs` (from GOAL-WC013)  
**Created:** 2026-07-29

xUnit test structure from WC-013: AAA pattern with FluentAssertions.

```
[Fact]
public async Task Method_Scenario_ExpectedResult()
{
    // Arrange
    var sut = new SomeClass(Mock.Of<IDep>());

    // Act
    var result = await sut.DoSomethingAsync();

    // Assert
    result.Should().NotBeNull();
    result.SomeProperty.Should().Be(expectedValue);
}
```


---

### DOTNET-TEST-WC013-CCT_EF01_C043BudgetCeilingEvaluatorTests.cs

**Status:** CANDIDATE  
**Category:** test-structure  
**Confidence:** 0.5  
**Source:** `tests/constitutional-engine.Tests/Evaluators/CCT_EF01_C043BudgetCeilingEvaluatorTests.cs` (from GOAL-WC013)  
**Created:** 2026-07-29

xUnit test structure from WC-013: AAA pattern with FluentAssertions.

```
[Fact]
public async Task Method_Scenario_ExpectedResult()
{
    // Arrange
    var sut = new SomeClass(Mock.Of<IDep>());

    // Act
    var result = await sut.DoSomethingAsync();

    // Assert
    result.Should().NotBeNull();
    result.SomeProperty.Should().Be(expectedValue);
}
```


---

### DOTNET-ANNO-WC013-CCT_EF01_EvidenceFirstTests.cs

**Status:** CANDIDATE  
**Category:** annotations  
**Confidence:** 0.5  
**Source:** `tests/constitutional-engine.Tests/Services/CCT_EF01_EvidenceFirstTests.cs` (from GOAL-WC013)  
**Created:** 2026-07-29

Constitutional annotation pattern confirmed in WC-013 (C-059 + C-073).

```
// Implements: architecture/reference/components/{service}.md §{Section}
// Constitutional basis: C-NNN ({Claim Name})
```


---

### DOTNET-TEST-WC013-CCT_EF01_EvidenceFirstTests.cs

**Status:** CANDIDATE  
**Category:** test-structure  
**Confidence:** 0.5  
**Source:** `tests/constitutional-engine.Tests/Services/CCT_EF01_EvidenceFirstTests.cs` (from GOAL-WC013)  
**Created:** 2026-07-29

xUnit test structure from WC-013: AAA pattern with FluentAssertions.

```
[Fact]
public async Task Method_Scenario_ExpectedResult()
{
    // Arrange
    var sut = new SomeClass(Mock.Of<IDep>());

    // Act
    var result = await sut.DoSomethingAsync();

    // Assert
    result.Should().NotBeNull();
    result.SomeProperty.Should().Be(expectedValue);
}
```


---
