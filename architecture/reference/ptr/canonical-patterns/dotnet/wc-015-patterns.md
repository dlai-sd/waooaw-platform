# Canonical Patterns — WC-015 (dotnet)

**Status:** CANDIDATE — awaiting Constitutional Analyst review  

**Source sprint:** WC-015  

**Extracted:** 2026-07-30  

**Confidence:** 0.5 (CANDIDATE) — promoted to 1.0 after CA review


---

### DOTNET-TEST-WC015-CCT_MT01_TenantIsolationTests.cs

**Status:** CANDIDATE  
**Category:** test-structure  
**Confidence:** 0.5  
**Source:** `tests/business-platform.Tests/Infrastructure/CCT_MT01_TenantIsolationTests.cs` (from GOAL-WC015)  
**Created:** 2026-07-30

xUnit test structure from WC-015: AAA pattern with FluentAssertions.

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

### DOTNET-ANNO-WC015-C041ToolAuthorizationEvaluator.cs

**Status:** CANDIDATE  
**Category:** annotations  
**Confidence:** 0.5  
**Source:** `src/constitutional-engine/Evaluators/C041ToolAuthorizationEvaluator.cs` (from GOAL-WC015)  
**Created:** 2026-07-30

Constitutional annotation pattern confirmed in WC-015 (C-059 + C-073).

```
// Implements: architecture/reference/components/{service}.md §{Section}
// Constitutional basis: C-NNN ({Claim Name})
```


---

### DOTNET-ANNO-WC015-C043BudgetCeilingEvaluator.cs

**Status:** CANDIDATE  
**Category:** annotations  
**Confidence:** 0.5  
**Source:** `src/constitutional-engine/Evaluators/C043BudgetCeilingEvaluator.cs` (from GOAL-WC015)  
**Created:** 2026-07-30

Constitutional annotation pattern confirmed in WC-015 (C-059 + C-073).

```
// Implements: architecture/reference/components/{service}.md §{Section}
// Constitutional basis: C-NNN ({Claim Name})
```


---

### DOTNET-ANNO-WC015-C048NonExploitationEvaluator.cs

**Status:** CANDIDATE  
**Category:** annotations  
**Confidence:** 0.5  
**Source:** `src/constitutional-engine/Evaluators/C048NonExploitationEvaluator.cs` (from GOAL-WC015)  
**Created:** 2026-07-30

Constitutional annotation pattern confirmed in WC-015 (C-059 + C-073).

```
// Implements: architecture/reference/components/{service}.md §{Section}
// Constitutional basis: C-NNN ({Claim Name})
```


---

### DOTNET-ANNO-WC015-C049HonestLimitationEvaluator.cs

**Status:** CANDIDATE  
**Category:** annotations  
**Confidence:** 0.5  
**Source:** `src/constitutional-engine/Evaluators/C049HonestLimitationEvaluator.cs` (from GOAL-WC015)  
**Created:** 2026-07-30

Constitutional annotation pattern confirmed in WC-015 (C-059 + C-073).

```
// Implements: architecture/reference/components/{service}.md §{Section}
// Constitutional basis: C-NNN ({Claim Name})
```


---
