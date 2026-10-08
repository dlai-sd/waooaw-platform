// Implements: WC-115 R055-R062, R067-R071, R096
// Constitutional basis: C-001, C-023, C-026, C-059, C-076, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using System.Text.Json;
using System.Text.Json.Nodes;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ConversationalEmploymentServiceTests
{
    [Fact(DisplayName = "CEW-FIT-06 identical command replay is stable")]
    public void IdenticalCommandReplaysAndChangedPayloadConflicts()
    {
        var service = new ConversationalEmploymentService();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var actorId = Guid.NewGuid();
        var idempotencyKey = Guid.NewGuid();
        service.RegisterWorkspace(Workspace(tenantId, relationshipId));
        var command = Json(
            """
            {
              "schemaVersion": "1.0",
              "kind": "CONFIRM_INDUCTION_ITEM",
              "subjectRef": "requirement-1",
              "expectedWorkspaceVersion": "workspace-1",
              "expectedManifestVersion": "manifest-1"
            }
            """
        );

        var accepted = service.Submit(tenantId, relationshipId, actorId, idempotencyKey, command);
        var replayed = service.Submit(tenantId, relationshipId, actorId, idempotencyKey, command);

        Assert.False(accepted.Replayed);
        Assert.True(replayed.Replayed);
        Assert.Equal(accepted.Receipt.CommandId, replayed.Receipt.CommandId);
        var changed = Json(
            """
            {
              "schemaVersion": "1.0",
              "kind": "CONFIRM_INDUCTION_ITEM",
              "subjectRef": "requirement-2",
              "expectedWorkspaceVersion": "workspace-1",
              "expectedManifestVersion": "manifest-1"
            }
            """
        );
        var error = Assert.Throws<EmploymentProtocolException>(() =>
            service.Submit(tenantId, relationshipId, actorId, idempotencyKey, changed)
        );
        Assert.Equal("EMPLOYMENT_IDEMPOTENCY_CONFLICT", error.Code);
    }

    [Fact]
    public void MissingWorkspaceReadsAndCommandsRemainNotAccessible()
    {
        var service = new ConversationalEmploymentService();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();

        Assert.Null(service.GetWorkspace(tenantId, relationshipId));
        Assert.Equal(
            "EMPLOYMENT_NOT_ACCESSIBLE",
            Assert
                .Throws<EmploymentProtocolException>(() =>
                    service.Submit(
                        tenantId,
                        relationshipId,
                        Guid.NewGuid(),
                        Guid.NewGuid(),
                        ValidConfirmCommand()
                    )
                )
                .Code
        );
    }

    [Fact]
    public void PersistenceLoadsAndCachesWorkspaceAndCommands()
    {
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var snapshot = Workspace(tenantId, relationshipId);
        var commandId = Guid.NewGuid();
        var outcome = PersistedOutcome(commandId);
        var persistence = new RecordingPersistence
        {
            WorkspaceToLoad = snapshot,
            CommandToLoad = outcome,
        };
        var service = new ConversationalEmploymentService(persistence);

        Assert.Same(snapshot, service.GetWorkspace(tenantId, relationshipId));
        Assert.Same(snapshot, service.GetWorkspace(tenantId, relationshipId));
        Assert.Same(outcome, service.GetCommand(tenantId, relationshipId, commandId));
        Assert.Same(outcome, service.GetCommand(tenantId, relationshipId, commandId));

        Assert.Equal(1, persistence.WorkspaceLoadCount);
        Assert.Equal(1, persistence.CommandLoadCount);
    }

    [Fact]
    public void PersistenceReservesReplaysAndAppendsOwnerOutcomes()
    {
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var persistence = new RecordingPersistence { ReserveAsReplay = true };
        var service = new ConversationalEmploymentService(persistence);
        service.RegisterWorkspace(Workspace(tenantId, relationshipId));

        var submission = service.Submit(
            tenantId,
            relationshipId,
            Guid.NewGuid(),
            Guid.NewGuid(),
            ValidConfirmCommand()
        );
        var updated = service.UpdateOwnerStep(
            tenantId,
            relationshipId,
            submission.Receipt.CommandId,
            "DOMAIN_ADAPTER",
            "ACCEPTED",
            null,
            null,
            "evidence:domain"
        );

        Assert.True(submission.Replayed);
        Assert.Equal("PARTIAL", updated.State);
        Assert.Equal(1, persistence.WorkspaceAppendCount);
        Assert.Equal(1, persistence.ReserveCount);
        Assert.Same(updated, persistence.AppendedOutcome);
    }

    [Fact]
    public void PersistenceDigestMismatchFailsClosed()
    {
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var persistence = new RecordingPersistence { ReservedDigest = "mismatched-digest" };
        var service = new ConversationalEmploymentService(persistence);
        service.RegisterWorkspace(Workspace(tenantId, relationshipId));

        var error = Assert.Throws<EmploymentProtocolException>(() =>
            service.Submit(
                tenantId,
                relationshipId,
                Guid.NewGuid(),
                Guid.NewGuid(),
                ValidConfirmCommand()
            )
        );

        Assert.Equal("EMPLOYMENT_IDEMPOTENCY_CONFLICT", error.Code);
    }

    [Fact(DisplayName = "CEW-FIT-04 CE evidence precedes governed success")]
    public void CommandCompletesOnlyAfterEveryOwnerIncludingCeSucceeds()
    {
        var service = new ConversationalEmploymentService();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        service.RegisterWorkspace(Workspace(tenantId, relationshipId));
        var submission = service.Submit(
            tenantId,
            relationshipId,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Json(
                """
                {
                  "schemaVersion": "1.0",
                  "kind": "CONFIRM_INDUCTION_ITEM",
                  "subjectRef": "requirement-1",
                  "expectedWorkspaceVersion": "workspace-1",
                  "expectedManifestVersion": "manifest-1"
                }
                """
            )
        );

        Assert.DoesNotContain(submission.Outcome.OwnerSteps, step => step.Owner == "PR");
        Assert.DoesNotContain(submission.Outcome.OwnerSteps, step => step.Owner == "WBE");
        foreach (var owner in new[] { "DOMAIN_ADAPTER" })
        {
            var partial = service.UpdateOwnerStep(
                tenantId,
                relationshipId,
                submission.Receipt.CommandId,
                owner,
                "COMPLETED",
                $"{owner.ToLowerInvariant()}-command",
                "source-1",
                $"evidence:{owner}"
            );
            Assert.Equal("PARTIAL", partial.State);
        }
        var completed = service.UpdateOwnerStep(
            tenantId,
            relationshipId,
            submission.Receipt.CommandId,
            "CE",
            "COMPLETED",
            "ce-decision-1",
            "decision-space-1",
            "evidence:CE"
        );

        Assert.Equal("COMPLETED", completed.State);
        Assert.Null(completed.Limitation);
        Assert.Contains("evidence:CE", completed.EvidenceRefs);
    }

    [Fact]
    public void CommandOwnerMatrixIncludesWbeOnlyForCommerciallyBoundCommandsAndNeverPr()
    {
        var service = new ConversationalEmploymentService();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        service.RegisterWorkspace(Workspace(tenantId, relationshipId));
        var accepted = service.Submit(
            tenantId,
            relationshipId,
            Guid.NewGuid(),
            Guid.NewGuid(),
            Json(
                """
                {
                  "schemaVersion": "1.0",
                  "kind": "ACCEPT_PLAN_VERSION",
                  "subjectRef": "plan-1",
                  "expectedWorkspaceVersion": "workspace-1",
                  "expectedManifestVersion": "manifest-1",
                  "expectedPlanVersion": "plan-1",
                  "expectedDecisionSpaceVersion": 1,
                  "expectedWbeSourceVersion": "wbe-1",
                  "acknowledgement": "I accept this exact plan."
                }
                """
            )
        );

        Assert.Equal(
            ["BP", "DOMAIN_ADAPTER", "WBE", "CE"],
            accepted.Outcome.OwnerSteps.Select(step => step.Owner)
        );
        Assert.DoesNotContain(accepted.Outcome.OwnerSteps, step => step.Owner == "PR");
    }

    [Fact]
    public void EveryClosedCommandVariantIsAcceptedWithoutInventedFields()
    {
        string[] commands =
        [
            """
                {"schemaVersion":"1.0","kind":"DEFER_INDUCTION_ITEM","subjectRef":"requirement-1","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","deferredReason":"Customer supplied reason","blockedSkillRefs":["skill-1"]}
                """,
            $$"""
                {"schemaVersion":"1.0","kind":"APPLY_CANDIDATE_PATCH","subjectRef":"patch-1","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","candidatePatchRef":"{{Guid.NewGuid():D}}"}
                """,
            """
                {"schemaVersion":"1.0","kind":"SUBMIT_PLAN_FOR_REVIEW","subjectRef":"plan-1","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","expectedPlanVersion":"plan-1"}
                """,
            """
                {"schemaVersion":"1.0","kind":"ACKNOWLEDGE_MATERIAL_CHANGE","subjectRef":"patch-1","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","expectedPlanVersion":"plan-1","expectedDecisionSpaceVersion":1,"expectedWbeSourceVersion":"wbe-1","acknowledgement":"I acknowledge the material change."}
                """,
            $$$"""
                {"schemaVersion":"1.0","kind":"RESCHEDULE_WITHIN_TOLERANCE","subjectRef":"commitment-1","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","expectedPlanVersion":"plan-1","requestedCalendarCommitment":{"commitmentId":"{{{Guid.NewGuid():D}}}","timeZone":"Asia/Kolkata","localDateTime":"2026-10-08T10:00:00","utcInstant":"2026-10-08T04:30:00Z","utcOffset":"+05:30","fold":0,"tzdbVersion":"2026a","tolerancePolicy":{"policyRef":"calendar-policy","policyVersion":"1"}},"acknowledgement":"I acknowledge this bounded reschedule."}
                """,
            $$$"""
                {"schemaVersion":"1.0","kind":"RESCHEDULE_WITHIN_TOLERANCE","subjectRef":"commitment-2","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","expectedPlanVersion":"plan-1","requestedCalendarCommitment":{"commitmentId":"{{{Guid.NewGuid():D}}}","timeZone":"America/New_York","localDateTime":"2026-11-01T01:30:00","utcInstant":"2026-11-01T06:30:00Z","utcOffset":"-05:00","fold":1,"tzdbVersion":"2026a","tolerancePolicy":{"policyRef":"calendar-policy","policyVersion":"1"}},"acknowledgement":"I acknowledge this bounded reschedule."}
                """,
            """
                {"schemaVersion":"1.0","kind":"REQUEST_REASSESSMENT","subjectRef":"review-1","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","expectedPlanVersion":"plan-1"}
                """,
            """
                {"schemaVersion":"1.0","kind":"ACKNOWLEDGE_CORRECTIVE_PROPOSAL","subjectRef":"corrective-1","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","acknowledgement":"I acknowledge the corrective proposal."}
                """,
        ];

        foreach (var command in commands)
        {
            var service = new ConversationalEmploymentService();
            var tenantId = Guid.NewGuid();
            var relationshipId = Guid.NewGuid();
            service.RegisterWorkspace(Workspace(tenantId, relationshipId));

            var result = service.Submit(
                tenantId,
                relationshipId,
                Guid.NewGuid(),
                Guid.NewGuid(),
                Json(command)
            );

            Assert.Equal("ACCEPTED", result.Receipt.State);
            Assert.DoesNotContain(result.Outcome.OwnerSteps, step => step.Owner == "PR");
        }
    }

    [Fact]
    public void DiscriminatorRejectsExtraOrMalformedCommandFields()
    {
        var service = new ConversationalEmploymentService();
        var error = Assert.Throws<EmploymentProtocolException>(() =>
            service.Submit(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                Json(
                    """
                    {
                      "schemaVersion": "1.0",
                      "kind": "APPLY_CANDIDATE_PATCH",
                      "subjectRef": "proposal",
                      "expectedWorkspaceVersion": "workspace-1",
                      "expectedManifestVersion": "manifest-1",
                      "candidatePatchRef": "not-a-uuid",
                      "inventedAuthority": true
                    }
                    """
                )
            )
        );

        Assert.Equal("EMPLOYMENT_INVALID_REQUEST", error.Code);
    }

    [Fact]
    public void ClosedCommandVariantsRejectMissingOrInvalidDiscriminatorFields()
    {
        string[] commands =
        [
            """{"schemaVersion":"1.0","kind":"UNKNOWN","subjectRef":"item","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1"}""",
            """{"schemaVersion":"2.0","kind":"CONFIRM_INDUCTION_ITEM","subjectRef":"item","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1"}""",
            """{"schemaVersion":"1.0","kind":"CONFIRM_INDUCTION_ITEM","subjectRef":1,"expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1"}""",
            """{"schemaVersion":"1.0","kind":"DEFER_INDUCTION_ITEM","subjectRef":"item","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","deferredReason":"","blockedSkillRefs":[]}""",
            """{"schemaVersion":"1.0","kind":"DEFER_INDUCTION_ITEM","subjectRef":"item","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","deferredReason":"blocked","blockedSkillRefs":"skill-1"}""",
            """{"schemaVersion":"1.0","kind":"DEFER_INDUCTION_ITEM","subjectRef":"item","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","deferredReason":"blocked","blockedSkillRefs":[""]}""",
            """{"schemaVersion":"1.0","kind":"APPLY_CANDIDATE_PATCH","subjectRef":"patch","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","candidatePatchRef":"not-a-uuid"}""",
            """{"schemaVersion":"1.0","kind":"SUBMIT_PLAN_FOR_REVIEW","subjectRef":"plan","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","expectedPlanVersion":""}""",
            """{"schemaVersion":"1.0","kind":"ACCEPT_PLAN_VERSION","subjectRef":"plan","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","expectedPlanVersion":"plan-1","expectedDecisionSpaceVersion":0,"expectedWbeSourceVersion":"wbe-1","acknowledgement":"accept"}""",
            """{"schemaVersion":"1.0","kind":"ACCEPT_PLAN_VERSION","subjectRef":"plan","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","expectedPlanVersion":"plan-1","expectedDecisionSpaceVersion":"1","expectedWbeSourceVersion":"wbe-1","acknowledgement":"accept"}""",
            """{"schemaVersion":"1.0","kind":"ACKNOWLEDGE_MATERIAL_CHANGE","subjectRef":"patch","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","expectedPlanVersion":"plan-1","expectedDecisionSpaceVersion":1,"expectedWbeSourceVersion":"wbe-1","acknowledgement":""}""",
            """{"schemaVersion":"1.0","kind":"RESCHEDULE_WITHIN_TOLERANCE","subjectRef":"commitment","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","expectedPlanVersion":"plan-1","requestedCalendarCommitment":{},"acknowledgement":"reschedule"}""",
            """{"schemaVersion":"1.0","kind":"REQUEST_REASSESSMENT","subjectRef":"review","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1"}""",
            """{"schemaVersion":"1.0","kind":"ACKNOWLEDGE_CORRECTIVE_PROPOSAL","subjectRef":"corrective","expectedWorkspaceVersion":"workspace-1","expectedManifestVersion":"manifest-1","acknowledgement":""}""",
        ];

        foreach (var command in commands)
        {
            var service = new ConversationalEmploymentService();
            var tenantId = Guid.NewGuid();
            var relationshipId = Guid.NewGuid();
            service.RegisterWorkspace(Workspace(tenantId, relationshipId));

            Assert.Equal(
                "EMPLOYMENT_INVALID_REQUEST",
                Assert
                    .Throws<EmploymentProtocolException>(() =>
                        service.Submit(
                            tenantId,
                            relationshipId,
                            Guid.NewGuid(),
                            Guid.NewGuid(),
                            Json(command)
                        )
                    )
                    .Code
            );
        }
    }

    [Theory(DisplayName = "CEW-FIT-09 non-success owner states remain distinct")]
    [InlineData("UNKNOWN", "UNKNOWN")]
    [InlineData("FAILED", "REJECTED")]
    [InlineData("BLOCKED", "BLOCKED")]
    public void OwnerFailuresProduceStableNonSuccessOutcomes(string ownerState, string commandState)
    {
        var service = new ConversationalEmploymentService();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        service.RegisterWorkspace(Workspace(tenantId, relationshipId));
        var submission = service.Submit(
            tenantId,
            relationshipId,
            Guid.NewGuid(),
            Guid.NewGuid(),
            ValidConfirmCommand()
        );

        var outcome = service.UpdateOwnerStep(
            tenantId,
            relationshipId,
            submission.Receipt.CommandId,
            "DOMAIN_ADAPTER",
            ownerState,
            null,
            null,
            $"evidence:{ownerState}"
        );

        Assert.Equal(commandState, outcome.State);
        Assert.NotNull(outcome.Limitation);
        if (commandState == "BLOCKED")
        {
            var error = Assert.Throws<EmploymentProtocolException>(() =>
                service.UpdateOwnerStep(
                    tenantId,
                    relationshipId,
                    submission.Receipt.CommandId,
                    "CE",
                    "COMPLETED",
                    null,
                    null,
                    "late"
                )
            );
            Assert.Equal("EMPLOYMENT_COMMAND_TERMINAL", error.Code);
        }
    }

    [Fact]
    public void OwnerUpdatesRejectMissingCommandsAndIncompleteOwnerEvidence()
    {
        var service = new ConversationalEmploymentService();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        service.RegisterWorkspace(Workspace(tenantId, relationshipId));
        Assert.Null(service.GetCommand(tenantId, relationshipId, Guid.NewGuid()));
        Assert.Equal(
            "EMPLOYMENT_NOT_ACCESSIBLE",
            Assert
                .Throws<EmploymentProtocolException>(() =>
                    service.UpdateOwnerStep(
                        tenantId,
                        relationshipId,
                        Guid.NewGuid(),
                        "CE",
                        "COMPLETED",
                        "owner-ref",
                        "source-1",
                        "evidence-1"
                    )
                )
                .Code
        );
        var submission = service.Submit(
            tenantId,
            relationshipId,
            Guid.NewGuid(),
            Guid.NewGuid(),
            ValidConfirmCommand()
        );
        foreach (
            var invalid in new[]
            {
                new
                {
                    Owner = "BP",
                    State = "COMPLETED",
                    OwnerRef = "owner-ref",
                    Source = "source-1",
                    Evidence = "evidence-1",
                },
                new
                {
                    Owner = "PR",
                    State = "COMPLETED",
                    OwnerRef = "owner-ref",
                    Source = "source-1",
                    Evidence = "evidence-1",
                },
                new
                {
                    Owner = "CE",
                    State = "INVALID",
                    OwnerRef = "owner-ref",
                    Source = "source-1",
                    Evidence = "evidence-1",
                },
                new
                {
                    Owner = "CE",
                    State = "COMPLETED",
                    OwnerRef = "",
                    Source = "source-1",
                    Evidence = "evidence-1",
                },
                new
                {
                    Owner = "CE",
                    State = "COMPLETED",
                    OwnerRef = "owner-ref",
                    Source = "",
                    Evidence = "evidence-1",
                },
                new
                {
                    Owner = "CE",
                    State = "BLOCKED",
                    OwnerRef = "owner-ref",
                    Source = "source-1",
                    Evidence = "",
                },
            }
        )
        {
            Assert.Equal(
                "EMPLOYMENT_INVALID_REQUEST",
                Assert
                    .Throws<EmploymentProtocolException>(() =>
                        service.UpdateOwnerStep(
                            tenantId,
                            relationshipId,
                            submission.Receipt.CommandId,
                            invalid.Owner,
                            invalid.State,
                            invalid.OwnerRef,
                            invalid.Source,
                            invalid.Evidence
                        )
                    )
                    .Code
            );
        }
    }

    [Fact(DisplayName = "CEW-FIT-12 Stop remains reachable in the aggregate")]
    public void WorkspaceAndVersionValidationFailClosed()
    {
        var service = new ConversationalEmploymentService();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var invalid = Workspace(tenantId, relationshipId) with
        {
            Workspace = Json("""{"operations":{"stopReachable":false}}"""),
        };
        Assert.Equal(
            "EMPLOYMENT_INVALID_REQUEST",
            Assert
                .Throws<EmploymentProtocolException>(() => service.RegisterWorkspace(invalid))
                .Code
        );
        service.RegisterWorkspace(Workspace(tenantId, relationshipId));
        Assert.NotNull(service.GetWorkspace(tenantId, relationshipId));
        Assert.Equal(
            "EMPLOYMENT_VERSION_CONFLICT",
            Assert
                .Throws<EmploymentProtocolException>(() =>
                    service.RegisterWorkspace(Workspace(tenantId, relationshipId))
                )
                .Code
        );
        var next = Workspace(tenantId, relationshipId);
        var nextAggregate = JsonNode.Parse(next.Workspace.GetRawText())!.AsObject();
        nextAggregate["workspaceVersion"] = "workspace-2";
        service.RegisterWorkspace(
            next with
            {
                WorkspaceVersion = "workspace-2",
                Workspace = JsonSerializer.SerializeToElement(nextAggregate),
            }
        );
        Assert.Equal(
            "workspace-2",
            service.GetWorkspace(tenantId, relationshipId)?.WorkspaceVersion
        );
        var stale = Json(
            """
            {
              "schemaVersion": "1.0",
              "kind": "CONFIRM_INDUCTION_ITEM",
              "subjectRef": "requirement-1",
              "expectedWorkspaceVersion": "stale",
              "expectedManifestVersion": "manifest-1"
            }
            """
        );
        Assert.Equal(
            "EMPLOYMENT_VERSION_CONFLICT",
            Assert
                .Throws<EmploymentProtocolException>(() =>
                    service.Submit(tenantId, relationshipId, Guid.NewGuid(), Guid.NewGuid(), stale)
                )
                .Code
        );
    }

    [Fact(DisplayName = "CEW-FIT-03 incomplete pending items are rejected")]
    public void IncompletePendingItemsAreRejected()
    {
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var snapshot = Workspace(tenantId, relationshipId);
        var workspace = JsonNode.Parse(snapshot.Workspace.GetRawText())!.AsObject();
        var induction = workspace["phases"]![0]!.AsObject();
        induction["pendingItems"] = new JsonArray(
            JsonNode.Parse("""{"itemId":"00000000-0000-0000-0000-000000000001"}""")
        );
        var invalidPhase = JsonSerializer.SerializeToElement(induction);
        var invalid = snapshot with
        {
            Workspace = JsonSerializer.SerializeToElement(workspace),
            Phases = new Dictionary<string, JsonElement>(snapshot.Phases)
            {
                ["INDUCTION"] = invalidPhase,
            },
        };

        var error = Assert.Throws<EmploymentProtocolException>(() =>
            new ConversationalEmploymentService().RegisterWorkspace(invalid)
        );

        Assert.Equal("EMPLOYMENT_INVALID_REQUEST", error.Code);
    }

    [Fact(DisplayName = "CEW-NEG-005 Operations cannot serialize COMPLETE")]
    public void OperationsCannotSerializeComplete()
    {
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var snapshot = Workspace(tenantId, relationshipId);
        var workspace = JsonNode.Parse(snapshot.Workspace.GetRawText())!.AsObject();
        var operations = workspace["phases"]![2]!.AsObject();
        operations["status"] = "COMPLETE";
        var invalidPhase = JsonSerializer.SerializeToElement(operations);
        var invalid = snapshot with
        {
            Workspace = JsonSerializer.SerializeToElement(workspace),
            Phases = new Dictionary<string, JsonElement>(snapshot.Phases)
            {
                ["OPERATIONS"] = invalidPhase,
            },
        };

        var error = Assert.Throws<EmploymentProtocolException>(() =>
            new ConversationalEmploymentService().RegisterWorkspace(invalid)
        );

        Assert.Equal("EMPLOYMENT_INVALID_REQUEST", error.Code);
    }

    [Fact]
    public void ClosedWorkspaceAggregateRejectsMalformedRootFields()
    {
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        Action<JsonObject>[] mutations =
        [
            workspace => workspace["schemaVersion"] = "2.0",
            workspace => workspace["protocolVersion"] = "active",
            workspace => workspace["relationshipId"] = Guid.NewGuid(),
            workspace => workspace["relationshipId"] = 1,
            workspace => workspace["workspaceVersion"] = "",
            workspace => workspace["agentType"] = "",
            workspace => workspace["agentVersion"] = "",
            workspace => workspace["manifestVersion"] = "",
            workspace => workspace["sources"] = new JsonArray(),
            workspace => workspace["limitations"] = new JsonObject(),
            workspace => workspace["limitations"] = new JsonArray(""),
            workspace => workspace["availableCommands"] = new JsonObject(),
            workspace =>
                workspace["availableCommands"] = new JsonArray(
                    new JsonObject { ["kind"] = "UNKNOWN" }
                ),
            workspace => workspace["authoritativeCursor"] = "",
            workspace => workspace["producedAt"] = "not-a-date",
            workspace => workspace["producedAt"] = 1,
            workspace => workspace.Remove("readiness"),
            workspace => workspace.Remove("operations"),
            workspace => workspace["currentPlan"] = new JsonObject(),
        ];

        foreach (var mutate in mutations)
        {
            var snapshot = Workspace(tenantId, relationshipId);
            var workspace = JsonNode.Parse(snapshot.Workspace.GetRawText())!.AsObject();
            mutate(workspace);
            var invalid = snapshot with
            {
                Workspace = JsonSerializer.SerializeToElement(workspace),
            };

            Assert.Equal(
                "EMPLOYMENT_INVALID_REQUEST",
                Assert
                    .Throws<EmploymentProtocolException>(() =>
                        new ConversationalEmploymentService().RegisterWorkspace(invalid)
                    )
                    .Code
            );
        }
    }

    [Fact]
    public void SourceProvenanceIsClosedAndComplete()
    {
        Action<JsonNode>[] mutations =
        [
            source => source.AsObject().Remove("owner"),
            source => source["owner"] = "",
            source => source["owner"] = "AIR",
            source => source["contractVersion"] = "",
            source => source["sourceVersion"] = "",
            source => source["state"] = "",
            source => source["state"] = "READY",
            source => source["observedAt"] = "not-a-date",
            source => source["observedAt"] = 1,
            source => source["validUntil"] = "not-a-date",
            source => source["validUntil"] = DateTimeOffset.UtcNow.AddMinutes(-5),
            source => source["limitation"] = "",
            source => source["limitation"] = new string('x', 501),
            source => source["evidenceRef"] = "not-in-candidate-schema",
            source => source["inventedAuthority"] = true,
        ];

        foreach (var mutate in mutations)
        {
            var snapshot = Workspace(Guid.NewGuid(), Guid.NewGuid());
            var workspace = JsonNode.Parse(snapshot.Workspace.GetRawText())!.AsObject();
            mutate(workspace["sources"]![0]!);
            AssertInvalidWorkspace(
                snapshot with
                {
                    Workspace = JsonSerializer.SerializeToElement(workspace),
                }
            );
        }

        var scalarSnapshot = Workspace(Guid.NewGuid(), Guid.NewGuid());
        var scalarWorkspace = JsonNode.Parse(scalarSnapshot.Workspace.GetRawText())!.AsObject();
        scalarWorkspace["sources"]![0] = "not-a-source";
        AssertInvalidWorkspace(
            scalarSnapshot with
            {
                Workspace = JsonSerializer.SerializeToElement(scalarWorkspace),
            }
        );
    }

    [Fact]
    public void ReadinessIsClosedAndRequiresOwnerSources()
    {
        Action<JsonObject>[] mutations =
        [
            readiness => readiness.Remove("induction"),
            readiness => readiness["induction"] = "READY_NOW",
            readiness => readiness["plan"] = "ACCEPTED",
            readiness => readiness["operations"] = "READY",
            readiness => readiness["performance"] = "HEALTHY",
            readiness => readiness["unmetConditions"] = new JsonObject(),
            readiness => readiness["unmetConditions"] = new JsonArray(""),
            readiness => readiness["eligibleSkillRefs"] = new JsonArray(""),
            readiness => readiness["lockedSkillRefs"] = new JsonObject(),
            readiness => readiness["sources"] = new JsonObject(),
            readiness => readiness["sources"] = new JsonArray(),
            readiness => readiness["sources"]![0]!["owner"] = "",
            readiness => readiness["inventedReadiness"] = true,
        ];

        foreach (var mutate in mutations)
        {
            var snapshot = Workspace(Guid.NewGuid(), Guid.NewGuid());
            var workspace = JsonNode.Parse(snapshot.Workspace.GetRawText())!.AsObject();
            var readiness = workspace["readiness"]!.AsObject();
            mutate(readiness);
            var serializedReadiness = JsonSerializer.SerializeToElement(readiness);
            AssertInvalidWorkspace(
                snapshot with
                {
                    Workspace = JsonSerializer.SerializeToElement(workspace),
                    Readiness = serializedReadiness,
                }
            );
        }
    }

    [Fact]
    public void OperationsAreClosedAndStopMustRemainReachable()
    {
        Action<JsonObject>[] mutations =
        [
            operations => operations.Remove("mode"),
            operations => operations["mode"] = "DISABLED",
            operations => operations["eligibility"] = "UNKNOWN",
            operations => operations["stopReachable"] = false,
            operations => operations["eligibleSkillRefs"] = new JsonObject(),
            operations => operations["eligibleSkillRefs"] = new JsonArray(""),
            operations => operations["lockedSkillRefs"] = new JsonObject(),
            operations => operations["permittedOperationClasses"] = new JsonObject(),
            operations => operations["permittedOperationClasses"] = new JsonArray("CONSEQUENTIAL"),
            operations =>
                operations["permittedOperationClasses"] = new JsonArray("ADVISORY", "ADVISORY"),
            operations => operations["permittedOperationClasses"] = new JsonArray("INVENTED"),
            operations => operations["commercialSource"]!["owner"] = "",
            operations => operations["inventedOperation"] = true,
        ];

        foreach (var mutate in mutations)
        {
            var snapshot = Workspace(Guid.NewGuid(), Guid.NewGuid());
            var workspace = JsonNode.Parse(snapshot.Workspace.GetRawText())!.AsObject();
            mutate(workspace["operations"]!.AsObject());
            AssertInvalidWorkspace(
                snapshot with
                {
                    Workspace = JsonSerializer.SerializeToElement(workspace),
                }
            );
        }
    }

    [Fact]
    public void PhaseEvidenceAndItemCollectionsFailClosed()
    {
        Action<JsonObject>[] mutations =
        [
            phase => phase.Remove("status"),
            phase => phase["phase"] = "DELIVERY",
            phase => phase["status"] = "FINISHED",
            phase => phase["status"] = null,
            phase => phase["evidenceState"] = null,
            phase => phase["evidenceState"] = "READY",
            phase =>
            {
                phase["status"] = "ACTIVE";
                phase["evidenceState"] = "STALE";
            },
            phase => phase["sourceFreshness"] = "not-a-date",
            phase => phase["sourceFreshness"] = 1,
            phase => phase["progress"]!["mandatoryTotal"] = -1,
            phase =>
            {
                phase["progress"]!["mandatoryTotal"] = 1;
                phase["progress"]!["mandatoryCompleted"] = 2;
            },
            phase => phase["assumptions"] = new JsonArray(""),
            phase => phase["limitations"] = new JsonObject(),
            phase =>
                phase["availableCommands"] = new JsonArray(
                    new JsonObject
                    {
                        ["kind"] = "UNKNOWN",
                        ["subjectRef"] = "item-1",
                        ["requiresExplicitAcknowledgement"] = false,
                    }
                ),
            phase => phase["calendarCommitments"] = new JsonArray(new JsonObject()),
            phase => phase["sources"] = new JsonObject(),
            phase => phase["sources"] = new JsonArray(),
            phase => phase["sources"]![0]!["owner"] = "",
            phase => phase["completedItems"] = new JsonObject(),
            phase => phase["inProgressItems"] = new JsonObject(),
            phase => phase["pendingItems"] = new JsonObject(),
            phase => phase["blockers"] = new JsonObject(),
            phase => phase["dependencies"] = new JsonObject(),
            phase => phase["milestones"] = new JsonObject(),
            phase => phase["completedItems"] = new JsonArray("not-an-item"),
            phase => phase["inventedPhaseState"] = true,
        ];

        foreach (var mutate in mutations)
        {
            var snapshot = Workspace(Guid.NewGuid(), Guid.NewGuid());
            var workspace = JsonNode.Parse(snapshot.Workspace.GetRawText())!.AsObject();
            var phase = workspace["phases"]![0]!.AsObject();
            mutate(phase);
            AssertInvalidWorkspace(
                snapshot with
                {
                    Workspace = JsonSerializer.SerializeToElement(workspace),
                    Phases = new Dictionary<string, JsonElement>(snapshot.Phases)
                    {
                        ["INDUCTION"] = JsonSerializer.SerializeToElement(phase),
                    },
                }
            );
        }
    }

    [Fact]
    public void PlansAndWorkspaceItemsAreClosedAndComplete()
    {
        Action<JsonObject>[] planMutations =
        [
            plan => plan.Remove("goalRef"),
            plan => plan["planId"] = "not-a-uuid",
            plan => plan["planId"] = 1,
            plan => plan["planVersion"] = "",
            plan => plan["state"] = "ACCEPTED",
            plan => plan["goalRef"] = "",
            plan => plan["outcomeLabel"] = "",
            plan => plan["accountableOwner"] = "",
            plan => plan["skillRefs"] = new JsonObject(),
            plan => plan["skillRefs"] = new JsonArray(),
            plan => plan["skillRefs"] = new JsonArray(""),
            plan => plan["milestones"] = new JsonObject(),
            plan => plan["calendarCommitments"] = new JsonObject(),
            plan => plan["calendarCommitments"] = new JsonArray(new JsonObject()),
            plan => plan["source"]!["owner"] = "",
            plan => plan["inventedPlanState"] = true,
        ];
        Action<JsonObject>[] itemMutations =
        [
            item => item.Remove("state"),
            item => item["itemId"] = "not-a-uuid",
            item => item["itemId"] = 1,
            item => item["itemVersion"] = "",
            item => item["phase"] = "DELIVERY",
            item => item["state"] = "PENDING",
            item => item["label"] = "",
            item => item["reason"] = "",
            item => item["accountableOwner"] = "",
            item => item["mandatory"] = "yes",
            item => item["blockedEffects"] = new JsonObject(),
            item =>
                item["blockedEffects"] = new JsonArray(
                    new JsonObject { ["effectType"] = "UNKNOWN", ["effectRef"] = "skill-1" }
                ),
            item => item["source"] = "not-a-source",
            item => item["source"]!["owner"] = "",
            item => item["availableCommands"] = new JsonObject(),
            item =>
                item["availableCommands"] = new JsonArray(
                    new JsonObject
                    {
                        ["kind"] = "UNKNOWN",
                        ["subjectRef"] = "item-1",
                        ["requiresExplicitAcknowledgement"] = false,
                    }
                ),
            item => item["inventedItemState"] = true,
        ];

        foreach (var mutate in planMutations)
        {
            var snapshot = WorkspaceWithPlan(Guid.NewGuid(), Guid.NewGuid());
            var workspace = JsonNode.Parse(snapshot.Workspace.GetRawText())!.AsObject();
            var plan = workspace["currentPlan"]!.AsObject();
            mutate(plan);
            AssertInvalidWorkspace(
                snapshot with
                {
                    Workspace = JsonSerializer.SerializeToElement(workspace),
                    Plans = new Dictionary<string, JsonElement>
                    {
                        ["plan-1"] = JsonSerializer.SerializeToElement(plan),
                    },
                }
            );
        }

        foreach (var mutate in itemMutations)
        {
            var snapshot = WorkspaceWithPlan(Guid.NewGuid(), Guid.NewGuid());
            var workspace = JsonNode.Parse(snapshot.Workspace.GetRawText())!.AsObject();
            var plan = workspace["currentPlan"]!.AsObject();
            mutate(plan["milestones"]![0]!.AsObject());
            AssertInvalidWorkspace(
                snapshot with
                {
                    Workspace = JsonSerializer.SerializeToElement(workspace),
                    Plans = new Dictionary<string, JsonElement>
                    {
                        ["plan-1"] = JsonSerializer.SerializeToElement(plan),
                    },
                }
            );
        }
    }

    [Fact]
    public void CalendarAndDecisionSpaceValuesAreDeeplyValidated()
    {
        var service = new ConversationalEmploymentService();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        service.RegisterWorkspace(Workspace(tenantId, relationshipId));
        var malformed = Json(
            """
            {
              "schemaVersion": "1.0",
              "kind": "RESCHEDULE_WITHIN_TOLERANCE",
              "subjectRef": "commitment-1",
              "expectedWorkspaceVersion": "workspace-1",
              "expectedManifestVersion": "manifest-1",
              "expectedPlanVersion": "plan-1",
              "requestedCalendarCommitment": {
                "commitmentId": "not-a-uuid",
                "timeZone": "Asia/Kolkata",
                "localDateTime": "2026-10-08T10:00:00",
                "utcInstant": "2026-10-08T04:30:00Z",
                "utcOffset": "+05:30",
                "fold": 0,
                "tzdbVersion": "2026a",
                "tolerancePolicy": {}
              },
              "acknowledgement": "I acknowledge the bounded reschedule."
            }
            """
        );
        Assert.Equal(
            "EMPLOYMENT_INVALID_REQUEST",
            Assert
                .Throws<EmploymentProtocolException>(() =>
                    service.Submit(
                        tenantId,
                        relationshipId,
                        Guid.NewGuid(),
                        Guid.NewGuid(),
                        malformed
                    )
                )
                .Code
        );

        Action<JsonObject>[] commitmentMutations =
        [
            commitment => commitment.Remove("timeZone"),
            commitment => commitment["commitmentId"] = 1,
            commitment => commitment["timeZone"] = "",
            commitment => commitment["localDateTime"] = "",
            commitment => commitment["utcInstant"] = "not-a-date",
            commitment => commitment["utcInstant"] = 1,
            commitment => commitment["utcInstant"] = "2026-10-08T05:30:00Z",
            commitment => commitment["utcOffset"] = "",
            commitment => commitment["utcOffset"] = "+04:30",
            commitment => commitment["fold"] = "0",
            commitment => commitment["fold"] = 1,
            commitment => commitment["fold"] = 2,
            commitment => commitment["tzdbVersion"] = "",
            commitment => commitment["tolerancePolicy"] = "not-a-policy",
            commitment => commitment["tolerancePolicy"] = new JsonObject(),
            commitment => commitment["tolerancePolicy"]!["inventedTolerance"] = true,
            commitment => commitment["timeZone"] = "Not/A-Time-Zone",
            commitment =>
            {
                commitment["timeZone"] = "America/New_York";
                commitment["localDateTime"] = "2026-03-08T02:30:00";
                commitment["utcInstant"] = "2026-03-08T07:30:00Z";
                commitment["utcOffset"] = "-05:00";
            },
            commitment => commitment["inventedCalendarAuthority"] = true,
        ];
        foreach (var mutate in commitmentMutations)
        {
            var command = JsonNode
                .Parse(
                    $$"""
                    {
                      "schemaVersion": "1.0",
                      "kind": "RESCHEDULE_WITHIN_TOLERANCE",
                      "subjectRef": "commitment-1",
                      "expectedWorkspaceVersion": "workspace-1",
                      "expectedManifestVersion": "manifest-1",
                      "expectedPlanVersion": "plan-1",
                      "requestedCalendarCommitment": {
                        "commitmentId": "{{Guid.NewGuid():D}}",
                        "timeZone": "Asia/Kolkata",
                        "localDateTime": "2026-10-08T10:00:00",
                        "utcInstant": "2026-10-08T04:30:00Z",
                        "utcOffset": "+05:30",
                        "fold": 0,
                        "tzdbVersion": "2026a",
                        "tolerancePolicy": {"policyRef":"calendar-policy","policyVersion":"1"}
                      },
                      "acknowledgement": "I acknowledge the bounded reschedule."
                    }
                    """
                )!
                .AsObject();
            mutate(command["requestedCalendarCommitment"]!.AsObject());
            Assert.Equal(
                "EMPLOYMENT_INVALID_REQUEST",
                Assert
                    .Throws<EmploymentProtocolException>(() =>
                        service.Submit(
                            tenantId,
                            relationshipId,
                            Guid.NewGuid(),
                            Guid.NewGuid(),
                            JsonSerializer.SerializeToElement(command)
                        )
                    )
                    .Code
            );
        }
    }

    private static void AssertInvalidWorkspace(EmploymentWorkspaceSnapshot snapshot)
    {
        var error = Assert.Throws<EmploymentProtocolException>(() =>
            new ConversationalEmploymentService().RegisterWorkspace(snapshot)
        );
        Assert.Equal("EMPLOYMENT_INVALID_REQUEST", error.Code);
    }

    private static EmploymentWorkspaceSnapshot Workspace(Guid tenantId, Guid relationshipId)
    {
        var source = Source();
        var phases = new Dictionary<string, JsonElement>
        {
            ["INDUCTION"] = Phase("INDUCTION", source),
            ["PLANNING"] = Phase("PLANNING", source),
            ["OPERATIONS"] = Phase("OPERATIONS", source),
        };
        var readiness = JsonSerializer.SerializeToElement(
            new
            {
                induction = "NOT_STARTED",
                plan = "NO_PLAN",
                operations = "LOCKED",
                performance = "NOT_ESTABLISHED",
                unmetConditions = new[] { "Owner checks are pending." },
                sources = new[] { source },
            }
        );
        var workspace = JsonSerializer.SerializeToElement(
            new
            {
                schemaVersion = "1.0",
                protocolVersion = "1.0-candidate",
                relationshipId,
                workspaceVersion = "workspace-1",
                agentType = "neutral-professional",
                agentVersion = "1.0.0",
                manifestVersion = "manifest-1",
                readiness,
                phases = phases.Values,
                currentPlan = (object?)null,
                operations = new
                {
                    mode = "TRIAL_ADVISORY",
                    eligibility = "LOCKED",
                    eligibleSkillRefs = Array.Empty<string>(),
                    lockedSkillRefs = new[] { "skill-1" },
                    permittedOperationClasses = Array.Empty<string>(),
                    stopReachable = true,
                    commercialSource = source,
                },
                sources = new[] { source },
                limitations = new[] { "Owner checks are pending." },
                availableCommands = Array.Empty<object>(),
                authoritativeCursor = "cursor-1",
                producedAt = DateTimeOffset.UtcNow,
            }
        );
        return new EmploymentWorkspaceSnapshot(
            tenantId,
            relationshipId,
            "workspace-1",
            "manifest-1",
            workspace,
            phases,
            readiness,
            new Dictionary<string, JsonElement>(),
            null,
            1,
            "wbe-1"
        );
    }

    private static EmploymentWorkspaceSnapshot WorkspaceWithPlan(Guid tenantId, Guid relationshipId)
    {
        var snapshot = Workspace(tenantId, relationshipId);
        var source = Source();
        var plan = JsonSerializer.SerializeToElement(
            new
            {
                planId = Guid.NewGuid(),
                planVersion = "plan-1",
                state = "DRAFT",
                goalRef = "goal-1",
                outcomeLabel = "Governed outcome",
                accountableOwner = "DOMAIN_ADAPTER",
                skillRefs = new[] { "skill-1" },
                milestones = new[]
                {
                    new
                    {
                        itemId = Guid.NewGuid(),
                        itemVersion = "item-1",
                        phase = "PLANNING",
                        label = "Validate plan",
                        mandatory = true,
                        state = "PROPOSED",
                        reason = "Owner validation is required.",
                        accountableOwner = "DOMAIN_ADAPTER",
                        blockedEffects = Array.Empty<string>(),
                        source,
                        availableCommands = Array.Empty<object>(),
                    },
                },
                calendarCommitments = Array.Empty<object>(),
                source,
            }
        );
        var workspace = JsonNode.Parse(snapshot.Workspace.GetRawText())!.AsObject();
        workspace["currentPlan"] = JsonNode.Parse(plan.GetRawText());
        return snapshot with
        {
            Workspace = JsonSerializer.SerializeToElement(workspace),
            Plans = new Dictionary<string, JsonElement> { ["plan-1"] = plan },
            CurrentPlanVersion = "plan-1",
        };
    }

    private static EmploymentCommandOutcome PersistedOutcome(Guid commandId) =>
        new(
            "1.0",
            commandId,
            "ACCEPTED",
            DateTimeOffset.UtcNow,
            $"/commands/{commandId}",
            [
                new EmploymentOwnerStep("BP", "COMMITTED", commandId.ToString(), "workspace-1"),
                new EmploymentOwnerStep("DOMAIN_ADAPTER", "PENDING"),
                new EmploymentOwnerStep("CE", "PENDING"),
            ],
            [$"bp-command-accepted:{commandId}"],
            new EmploymentResultingVersions("workspace-1", null, "manifest-1", null, null),
            "Owner validation remains pending.",
            DateTimeOffset.UtcNow
        );

    private sealed class RecordingPersistence : IConversationalEmploymentPersistence
    {
        public EmploymentWorkspaceSnapshot? WorkspaceToLoad { get; init; }
        public EmploymentCommandOutcome? CommandToLoad { get; init; }
        public string? ReservedDigest { get; init; }
        public bool ReserveAsReplay { get; init; }
        public int WorkspaceLoadCount { get; private set; }
        public int WorkspaceAppendCount { get; private set; }
        public int CommandLoadCount { get; private set; }
        public int ReserveCount { get; private set; }
        public EmploymentCommandOutcome? AppendedOutcome { get; private set; }

        public EmploymentWorkspaceSnapshot? LoadWorkspace(Guid tenantId, Guid relationshipId)
        {
            WorkspaceLoadCount++;
            return WorkspaceToLoad;
        }

        public void AppendWorkspace(EmploymentWorkspaceSnapshot snapshot) => WorkspaceAppendCount++;

        public EmploymentCommandOutcome? LoadCommand(
            Guid tenantId,
            Guid relationshipId,
            Guid commandId
        )
        {
            CommandLoadCount++;
            return CommandToLoad;
        }

        public PersistedEmploymentCommand ReserveCommand(
            Guid tenantId,
            Guid relationshipId,
            Guid actorId,
            Guid idempotencyKey,
            string commandKind,
            string canonicalDigest,
            string expectedWorkspaceVersion,
            string expectedManifestVersion,
            EmploymentCommandOutcome proposed
        )
        {
            ReserveCount++;
            return new PersistedEmploymentCommand(
                ReservedDigest ?? canonicalDigest,
                proposed,
                ReserveAsReplay
            );
        }

        public void AppendCommandOutcome(
            Guid tenantId,
            Guid relationshipId,
            EmploymentCommandOutcome outcome
        ) => AppendedOutcome = outcome;

        public Guid EraseProjectionContent(
            Guid tenantId,
            Guid relationshipId,
            string authorityRef
        ) => throw new NotSupportedException();

        public void AppendOwnerContext(
            Guid tenantId,
            Guid relationshipId,
            EmploymentOwnerContext context
        ) => throw new NotSupportedException();

        public EmploymentOwnerContext? LoadOwnerContext(
            Guid tenantId,
            Guid relationshipId,
            string contextRef,
            string contextKind
        ) => throw new NotSupportedException();
    }

    private static JsonElement Phase(string phase, JsonElement source) =>
        JsonSerializer.SerializeToElement(
            new
            {
                phase,
                status = "DEGRADED",
                progress = new
                {
                    mandatoryTotal = 0,
                    mandatoryCompleted = 0,
                    optionalTotal = 0,
                    optionalCompleted = 0,
                    blockedCount = 0,
                    deferredCount = 0,
                },
                completedItems = Array.Empty<object>(),
                inProgressItems = Array.Empty<object>(),
                pendingItems = Array.Empty<object>(),
                blockers = Array.Empty<object>(),
                assumptions = Array.Empty<string>(),
                dependencies = Array.Empty<object>(),
                milestones = Array.Empty<object>(),
                calendarCommitments = Array.Empty<object>(),
                evidenceState = "UNKNOWN",
                sourceFreshness = DateTimeOffset.UtcNow,
                limitations = new[] { "Owner checks are pending." },
                availableCommands = Array.Empty<object>(),
                sources = new[] { source },
            }
        );

    private static JsonElement Source() =>
        JsonSerializer.SerializeToElement(
            new
            {
                owner = "BP",
                contractVersion = "1.0.0-candidate.2",
                sourceVersion = "workspace-1",
                state = "UNKNOWN",
                observedAt = DateTimeOffset.UtcNow,
                validUntil = DateTimeOffset.UtcNow.AddMinutes(5),
                limitation = "Owner validation remains pending.",
            }
        );

    private static JsonElement ValidConfirmCommand() =>
        Json(
            """
            {
              "schemaVersion": "1.0",
              "kind": "CONFIRM_INDUCTION_ITEM",
              "subjectRef": "requirement-1",
              "expectedWorkspaceVersion": "workspace-1",
              "expectedManifestVersion": "manifest-1"
            }
            """
        );

    private static JsonElement Json(string value)
    {
        using var document = JsonDocument.Parse(value);
        return document.RootElement.Clone();
    }
}
