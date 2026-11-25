// Implements: work-contracts/WC-170-real-agent-work-end-to-end.md WC170-R005, WC170-R006, WC170-R007, WC170-R008, WC170-R010
// Constitutional basis: C-001, C-005, C-023, C-049, C-059, C-076
// IB: IB-170

using System.Text.Json;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.RealWork;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class RealWorkTests
{
    private static readonly Guid Tenant = Guid.NewGuid();
    private static readonly Guid Relationship = Guid.NewGuid();
    private static readonly Guid Actor = Guid.NewGuid();

    [Fact]
    public void ADigestIgnoresPropertyOrderAndWhitespaceButNotArrayOrder()
    {
        var first = Json("""{"b":1,"a":[1,2]}""");
        var second = Json("""{ "a": [1, 2], "b": 1 }""");
        var reordered = Json("""{"a":[2,1],"b":1}""");

        Assert.Equal(RealWorkDigest.Of(first), RealWorkDigest.Of(second));
        Assert.NotEqual(RealWorkDigest.Of(first), RealWorkDigest.Of(reordered));
    }

    [Fact]
    public void ASuccessorNeverInheritsApprovalAndSupersedesItsPredecessorOnlyWhenLocked()
    {
        var h = new Harness();
        var first = h.Artifacts.Propose(Tenant, Relationship, Proposal("""{"goal":"leads"}"""));
        h.Artifacts.Lock(Tenant, Relationship, first.ArtifactId, first.Digest, Guid.NewGuid());

        var successor = h.Artifacts.Propose(
            Tenant,
            Relationship,
            Proposal("""{"goal":"visits"}""") with
            {
                SupersedesArtifactId = first.ArtifactId,
            }
        );

        Assert.Equal(2, successor.Version);
        Assert.Equal(ArtifactStatus.Proposed, successor.Status);
        Assert.Null(successor.ApprovalEvidenceId);
        Assert.Equal(
            ArtifactStatus.Locked,
            h.Artifacts.Get(Tenant, Relationship, first.ArtifactId)!.Status
        );

        h.Artifacts.Lock(
            Tenant,
            Relationship,
            successor.ArtifactId,
            successor.Digest,
            Guid.NewGuid()
        );
        Assert.Equal(
            ArtifactStatus.Superseded,
            h.Artifacts.Get(Tenant, Relationship, first.ArtifactId)!.Status
        );
    }

    [Fact]
    public void LockingNeedsGenuineEvidenceTheExactDigestAndAProposedVersion()
    {
        var h = new Harness();
        var artifact = h.Artifacts.Propose(Tenant, Relationship, Proposal("""{"a":1}"""));

        Assert.Equal(
            "REAL_WORK_APPROVAL_EVIDENCE_REQUIRED",
            Assert
                .Throws<RealWorkConflictException>(() =>
                    h.Artifacts.Lock(
                        Tenant,
                        Relationship,
                        artifact.ArtifactId,
                        artifact.Digest,
                        Guid.Empty
                    )
                )
                .Code
        );
        Assert.Equal(
            "REAL_WORK_DIGEST_MISMATCH",
            Assert
                .Throws<RealWorkConflictException>(() =>
                    h.Artifacts.Lock(
                        Tenant,
                        Relationship,
                        artifact.ArtifactId,
                        new string('0', 64),
                        Guid.NewGuid()
                    )
                )
                .Code
        );
        var draft = h.Artifacts.Propose(
            Tenant,
            Relationship,
            Proposal("""{"a":2}""") with
            {
                Draft = true,
            }
        );
        Assert.Equal(ArtifactStatus.Draft, draft.Status);
        Assert.Throws<RealWorkConflictException>(() =>
            h.Artifacts.Lock(Tenant, Relationship, draft.ArtifactId, draft.Digest, Guid.NewGuid())
        );
        Assert.Equal(
            ArtifactStatus.Proposed,
            h.Artifacts.Submit(Tenant, Relationship, draft.ArtifactId).Status
        );
    }

    [Fact]
    public void AnUnresolvedVocabularyTokenIsRefusedAndAnUnchangedSuccessorIsNoChange()
    {
        var h = new Harness();
        Assert.Equal(
            "REAL_WORK_UNRESOLVED_VOCABULARY",
            Assert
                .Throws<RealWorkConflictException>(() =>
                    h.Artifacts.Propose(
                        Tenant,
                        Relationship,
                        Proposal("""{"a":1}""") with
                        {
                            PlainLanguageSummary = "Grow your {DVE.CLIENT}",
                        }
                    )
                )
                .Code
        );
        var artifact = h.Artifacts.Propose(Tenant, Relationship, Proposal("""{"a":1}"""));
        Assert.Equal(
            artifact.Digest,
            h.Artifacts.Propose(Tenant, Relationship, Proposal("""{"a":1}""")).Digest
        );
        Assert.Equal(
            "REAL_WORK_NO_CHANGE",
            Assert
                .Throws<RealWorkConflictException>(() =>
                    h.Artifacts.Propose(
                        Tenant,
                        Relationship,
                        Proposal("""{"a":1}""") with
                        {
                            SupersedesArtifactId = artifact.ArtifactId,
                        }
                    )
                )
                .Code
        );
    }

    [Fact]
    public async Task ApprovalAndScopeConfirmationAreTwoOrderedStepsWithTwoRecords()
    {
        var h = new Harness();
        var artifact = h.Artifacts.Propose(Tenant, Relationship, Proposal("""{"brief":"b"}"""));

        Assert.Equal(
            "REAL_WORK_APPROVAL_REQUIRED_FIRST",
            (await Assert.ThrowsAsync<RealWorkConflictException>(() => h.Scope(artifact))).Code
        );
        var approval = await h.Approve(artifact);
        Assert.False(
            h.Decisions.Check(Tenant, Relationship, artifact.ArtifactId, artifact.Digest).Executable
        );
        Assert.Equal(
            "SCOPE_CONFIRMATION_MISSING",
            h.Decisions.Check(
                Tenant,
                Relationship,
                artifact.ArtifactId,
                artifact.Digest
            ).BlockedReason
        );
        var scope = await h.Scope(artifact);

        var state = h.Decisions.Check(Tenant, Relationship, artifact.ArtifactId, artifact.Digest);
        Assert.True(state.Executable);
        Assert.Equal(DecisionKinds.Approval, approval.Kind);
        Assert.Equal(DecisionKinds.ScopeConfirmation, scope.Kind);
        Assert.NotEqual(approval.EvidenceId, scope.EvidenceId);
        Assert.Equal(7L, scope.DecisionSpaceVersion);
        Assert.Equal(
            ["EMPLOYMENT_ACCEPT_ARTIFACT_VERSION", "EMPLOYMENT_CONFIRM_SCOPE_BOUNDARY"],
            h.Gateway.ActionTypes
        );
        Assert.Equal(
            ArtifactStatus.Locked,
            h.Artifacts.Get(Tenant, Relationship, artifact.ArtifactId)!.Status
        );
    }

    [Fact]
    public async Task AWrongDigestOrAConstitutionalDenialLeavesNothingApproved()
    {
        var h = new Harness();
        var artifact = h.Artifacts.Propose(Tenant, Relationship, Proposal("""{"brief":"b"}"""));

        await Assert.ThrowsAsync<RealWorkConflictException>(() =>
            h.Decisions.ApproveAsync(
                Tenant,
                Relationship,
                Actor,
                "agent",
                artifact.ArtifactId,
                new string('f', 64),
                Guid.NewGuid(),
                7,
                CancellationToken.None
            )
        );
        h.Gateway.Deny = true;
        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() => h.Approve(artifact));

        Assert.Equal(
            ArtifactStatus.Proposed,
            h.Artifacts.Get(Tenant, Relationship, artifact.ArtifactId)!.Status
        );
        Assert.Equal(
            "ARTIFACT_PROPOSED",
            h.Decisions.Check(
                Tenant,
                Relationship,
                artifact.ArtifactId,
                artifact.Digest
            ).BlockedReason
        );
    }

    [Fact]
    public async Task ACorrectionIsASuccessorThatNeedsItsOwnTwoDecisions()
    {
        var h = new Harness();
        var original = await h.Decided("""{"draft":"v1"}""");
        var correction = h.Artifacts.Propose(
            Tenant,
            Relationship,
            Proposal("""{"draft":"v2"}""") with
            {
                SupersedesArtifactId = original.ArtifactId,
            }
        );

        Assert.False(
            h.Decisions.Check(
                Tenant,
                Relationship,
                correction.ArtifactId,
                correction.Digest
            ).Executable
        );
        await h.Approve(correction);
        await h.Scope(correction);

        Assert.True(
            h.Decisions.Check(
                Tenant,
                Relationship,
                correction.ArtifactId,
                correction.Digest
            ).Executable
        );
        Assert.False(
            h.Decisions.Check(Tenant, Relationship, original.ArtifactId, original.Digest).Executable
        );
    }

    [Fact]
    public async Task ExecutionIsRefusedUnlessBothDecisionsExistForTheExactDigest()
    {
        var h = new Harness();
        var artifact = h.Artifacts.Propose(Tenant, Relationship, Proposal("""{"brief":"b"}"""));
        var work = Guid.NewGuid();

        Assert.Equal(
            "REAL_WORK_ARTIFACT_NOT_EXECUTABLE",
            Assert
                .Throws<RealWorkConflictException>(() =>
                    h.Timeline.Ingest(Tenant, Relationship, Event(work, "EXECUTING", artifact))
                )
                .Code
        );
        await h.Approve(artifact);
        await h.Scope(artifact);
        Assert.Throws<RealWorkConflictException>(() =>
            h.Timeline.Ingest(
                Tenant,
                Relationship,
                Event(work, "EXECUTING", artifact) with
                {
                    ArtifactDigest = new string('a', 64),
                }
            )
        );
        Assert.Throws<RealWorkConflictException>(() =>
            h.Timeline.Ingest(
                Tenant,
                Relationship,
                Event(work, "EXECUTING", artifact) with
                {
                    ArtifactId = null,
                    ArtifactDigest = null,
                }
            )
        );

        var accepted = h.Timeline.Ingest(Tenant, Relationship, Event(work, "EXECUTING", artifact));
        Assert.Equal("EXECUTING", accepted.State);
        Assert.Equal(artifact.Digest, accepted.ArtifactDigest);
    }

    [Fact]
    public void ArtifactCreatingStepsAreNotCircularAndProposalsNeedNoBinding()
    {
        var h = new Harness();
        var work = Guid.NewGuid();

        var proposed = h.Timeline.Ingest(
            Tenant,
            Relationship,
            new(Guid.NewGuid(), work, "PROFILE_CONFIRMATION", "PROPOSED", DateTimeOffset.UtcNow)
        );
        var executing = h.Timeline.Ingest(
            Tenant,
            Relationship,
            new(
                Guid.NewGuid(),
                work,
                "PROFILE_CONFIRMATION",
                "EXECUTING",
                DateTimeOffset.UtcNow,
                ProducesArtifact: true
            )
        );

        Assert.Equal("PROPOSED", proposed.State);
        Assert.Equal("EXECUTING", executing.State);
    }

    [Fact]
    public async Task ReplayAndReorderResolveToOneLogicalEventPerWorkItem()
    {
        var h = new Harness();
        var artifact = await h.Decided("""{"brief":"b"}""");
        var work = Guid.NewGuid();
        var done = Event(work, "COMPLETED", artifact) with { EvidenceRefs = ["ce-evidence:1"] };

        var first = h.Timeline.Ingest(Tenant, Relationship, done);
        var replay = h.Timeline.Ingest(Tenant, Relationship, done);
        h.Timeline.Ingest(Tenant, Relationship, Event(work, "EXECUTING", artifact));
        var view = h.Timeline.Read(Tenant, Relationship);

        Assert.Equal(first.Sequence, replay.Sequence);
        Assert.Equal(2, view.Events.Count);
        var item = Assert.Single(view.WorkItems);
        Assert.Equal("COMPLETED", item.State);
        Assert.Equal("The content item is done.", item.Sentence);
    }

    [Fact]
    public async Task PublicationCountsAsCompletedOnlyWithTheProvidersOwnReference()
    {
        var h = new Harness();
        var artifact = await h.Decided("""{"post":"p"}""");
        var work = Guid.NewGuid();
        var receipt = Event(work, "COMPLETED", artifact) with
        {
            WorkItemType = "SOCIAL_POST_PUBLICATION",
            RequiresProviderProof = true,
        };

        var accepted = h.Timeline.Ingest(Tenant, Relationship, receipt);
        Assert.Equal("EXECUTING", accepted.State);
        Assert.Equal("AWAITING_PROVIDER_PROOF", accepted.ReasonCode);

        var proven = h.Timeline.Ingest(
            Tenant,
            Relationship,
            receipt with
            {
                EventId = Guid.NewGuid(),
                ProviderReference = "page_123_post_456",
            }
        );
        Assert.Equal("COMPLETED", proven.State);
        Assert.Equal("page_123_post_456", proven.ProviderReference);
        Assert.Equal(
            "COMPLETED",
            Assert.Single(h.Timeline.Read(Tenant, Relationship).WorkItems).State
        );
    }

    [Fact]
    public async Task AnUnknownOutcomeIsReconciledAndNeverRetriedBlindly()
    {
        var h = new Harness();
        var artifact = await h.Decided("""{"post":"p"}""");
        var work = Guid.NewGuid();
        var unknown = h.Timeline.Ingest(
            Tenant,
            Relationship,
            Event(work, "EXECUTING", artifact) with
            {
                ReasonCode = "UNKNOWN_OUTCOME",
            }
        );
        Assert.Contains("do not know yet", unknown.Sentence);

        Assert.Equal(
            "REAL_WORK_BLIND_RETRY",
            Assert
                .Throws<RealWorkConflictException>(() =>
                    h.Timeline.Ingest(Tenant, Relationship, Event(work, "EXECUTING", artifact))
                )
                .Code
        );
        var reconciled = h.Timeline.Ingest(
            Tenant,
            Relationship,
            Event(work, "COMPLETED", artifact) with
            {
                ReasonCode = "RECONCILED",
                EvidenceRefs = ["provider-status:confirmed"],
            }
        );

        var item = Assert.Single(h.Timeline.Read(Tenant, Relationship).WorkItems);
        Assert.Equal("COMPLETED", reconciled.State);
        Assert.Equal("COMPLETED", item.State);
        Assert.Equal(2, item.Events.Count);
    }

    [Fact]
    public async Task EmergencyStopFencesTheStreamLateSuccessIsEvidenceAndOtherRelationshipsAreUnaffected()
    {
        var h = new Harness();
        var artifact = await h.Decided("""{"post":"p"}""");
        var other = Guid.NewGuid();
        var otherArtifact = await h.Decided("""{"post":"q"}""", other);
        var work = Guid.NewGuid();
        h.Timeline.Ingest(Tenant, Relationship, Event(work, "EXECUTING", artifact));

        h.Timeline.Ingest(
            Tenant,
            Relationship,
            new(
                Guid.NewGuid(),
                Guid.NewGuid(),
                RealWorkTimelineService.StopWorkItemType,
                "HALTED",
                DateTimeOffset.UtcNow,
                ReasonCode: "EMERGENCY_STOP"
            )
        );
        var late = h.Timeline.Ingest(
            Tenant,
            Relationship,
            Event(work, "COMPLETED", artifact) with
            {
                EvidenceRefs = ["late-provider-result"],
            }
        );
        var unaffected = h.Timeline.Ingest(
            Tenant,
            other,
            Event(Guid.NewGuid(), "COMPLETED", otherArtifact)
        );

        Assert.Equal("HALTED", late.State);
        Assert.Equal("EMERGENCY_STOP", late.ReasonCode);
        Assert.Contains("late-provider-result", late.EvidenceRefs);
        var view = h.Timeline.Read(Tenant, Relationship);
        Assert.True(view.EmergencyStopActive);
        Assert.Equal("HALTED", Assert.Single(view.WorkItems).State);
        Assert.Equal("COMPLETED", unaffected.State);
        Assert.False(h.Timeline.Read(Tenant, other).EmergencyStopActive);
    }

    [Fact]
    public void ASecretOrAnUnknownStateNeverEntersTheTimeline()
    {
        var h = new Harness();
        var work = Guid.NewGuid();

        Assert.Equal(
            "REAL_WORK_SECRET_REJECTED",
            Assert
                .Throws<RealWorkConflictException>(() =>
                    h.Timeline.Ingest(
                        Tenant,
                        Relationship,
                        new(Guid.NewGuid(), work, "POST", "PROPOSED", DateTimeOffset.UtcNow)
                        {
                            EvidenceRefs = ["Bearer abc.def"],
                        }
                    )
                )
                .Code
        );
        Assert.Equal(
            "REAL_WORK_INVALID_REQUEST",
            Assert
                .Throws<RealWorkConflictException>(() =>
                    h.Timeline.Ingest(
                        Tenant,
                        Relationship,
                        new(Guid.NewGuid(), work, "POST", "UNKNOWN", DateTimeOffset.UtcNow)
                    )
                )
                .Code
        );
        Assert.Throws<RealWorkConflictException>(() =>
            h.Timeline.Ingest(
                Tenant,
                Relationship,
                new(Guid.NewGuid(), work, "POST", "FAILED", DateTimeOffset.UtcNow)
            )
        );
    }

    [Fact]
    public async Task AScopeConfirmationGivenUnderAnOlderDecisionSpaceIsStaleAndBlocksExecution()
    {
        var h = new Harness();
        var artifact = await h.Decided("""{"brief":"b"}""");
        var current = new FixedVersions(7);
        var decisions = new RealWorkDecisionService(
            h.Ledger,
            h.Artifacts,
            h.Gateway,
            TimeProvider.System,
            current
        );

        Assert.True(
            decisions.Check(Tenant, Relationship, artifact.ArtifactId, artifact.Digest).Executable
        );
        current.Value = 8;
        var stale = decisions.Check(Tenant, Relationship, artifact.ArtifactId, artifact.Digest);

        Assert.False(stale.Executable);
        Assert.Equal("SCOPE_CONFIRMATION_STALE", stale.BlockedReason);
    }

    [Fact]
    public async Task APredecessorIsSupersededTheMomentItsSuccessorIsLocked()
    {
        var h = new Harness();
        var first = await h.Decided("""{"draft":"v1"}""");
        var successor = h.Artifacts.Propose(
            Tenant,
            Relationship,
            Proposal("""{"draft":"v2"}""") with
            {
                SupersedesArtifactId = first.ArtifactId,
            }
        );

        // Locking alone, with no separate supersession record, is enough to retire the predecessor.
        var records = h.Ledger as InMemoryRealWorkLedger;
        h.Artifacts.Lock(
            Tenant,
            Relationship,
            successor.ArtifactId,
            successor.Digest,
            Guid.NewGuid()
        );
        var folded = RealWorkArtifactService.Fold(
            records!
                .List(Tenant, Relationship)
                .Where(record => record.Kind != RealWorkKinds.ArtifactSuperseded)
                .ToArray()
        );

        Assert.Equal(
            ArtifactStatus.Superseded,
            folded.Single(item => item.ArtifactId == first.ArtifactId).Status
        );
    }

    [Fact]
    public async Task AnEventIdReusedWithDifferentContentIsAConflictNotAReplay()
    {
        var h = new Harness();
        var artifact = await h.Decided("""{"post":"p"}""");
        var work = Guid.NewGuid();
        var original = Event(work, "EXECUTING", artifact);
        h.Timeline.Ingest(Tenant, Relationship, original);

        Assert.Equal(
            "REAL_WORK_IDEMPOTENCY_CONFLICT",
            Assert
                .Throws<RealWorkConflictException>(() =>
                    h.Timeline.Ingest(
                        Tenant,
                        Relationship,
                        original with
                        {
                            WorkItemId = Guid.NewGuid(),
                        }
                    )
                )
                .Code
        );
    }

    [Fact]
    public async Task TheArtifactCreatingExemptionCannotCarryProviderProofOrABinding()
    {
        var h = new Harness();
        var artifact = await h.Decided("""{"post":"p"}""");

        foreach (
            var attempt in new[]
            {
                Event(Guid.NewGuid(), "EXECUTING", artifact) with
                {
                    ProducesArtifact = true,
                },
                new TimelineEventInput(
                    Guid.NewGuid(),
                    Guid.NewGuid(),
                    "SOCIAL_POST",
                    "COMPLETED",
                    DateTimeOffset.UtcNow,
                    ProducesArtifact: true,
                    RequiresProviderProof: true
                ),
            }
        )
            Assert.Equal(
                "REAL_WORK_INVALID_REQUEST",
                Assert
                    .Throws<RealWorkConflictException>(() =>
                        h.Timeline.Ingest(Tenant, Relationship, attempt)
                    )
                    .Code
            );
    }

    [Theory]
    [InlineData("has a space")]
    [InlineData("AbCdEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEfGh")]
    public void AnOpaqueOrFreeTextReferenceIsRefusedAsCredentialLike(string reference)
    {
        var h = new Harness();

        Assert.Equal(
            "REAL_WORK_SECRET_REJECTED",
            Assert
                .Throws<RealWorkConflictException>(() =>
                    h.Timeline.Ingest(
                        Tenant,
                        Relationship,
                        new(
                            Guid.NewGuid(),
                            Guid.NewGuid(),
                            "POST",
                            "PROPOSED",
                            DateTimeOffset.UtcNow
                        )
                        {
                            EvidenceRefs = [reference],
                        }
                    )
                )
                .Code
        );
    }

    [Fact]
    public void TheTimelineIsTenantScoped()
    {
        var h = new Harness();
        h.Timeline.Ingest(
            Tenant,
            Relationship,
            new(Guid.NewGuid(), Guid.NewGuid(), "POST", "PROPOSED", DateTimeOffset.UtcNow)
        );

        Assert.Empty(h.Timeline.Read(Guid.NewGuid(), Relationship).Events);
        Assert.Single(h.Timeline.Read(Tenant, Relationship).Events);
    }

    [Fact]
    public async Task ActivityIsDerivedFromCompletedWorkWithEvidenceAndIsNeverABusinessOutcome()
    {
        var h = new Harness();
        var artifact = await h.Decided("""{"post":"p"}""");
        foreach (var _ in Enumerable.Range(0, 2))
            h.Timeline.Ingest(
                Tenant,
                Relationship,
                Event(Guid.NewGuid(), "COMPLETED", artifact) with
                {
                    WorkItemType = "SOCIAL_POST",
                    EvidenceRefs = ["ev"],
                }
            );
        h.Timeline.Ingest(
            Tenant,
            Relationship,
            Event(Guid.NewGuid(), "COMPLETED", artifact) with
            {
                WorkItemType = "NO_EVIDENCE_ITEM",
            }
        );

        var view = h.Outcomes.Read(Tenant, Relationship);

        var claim = Assert.Single(view.Activity);
        Assert.Equal("2 social post completed", claim.ClaimText);
        Assert.Equal("INDEPENDENT", claim.Derivation);
        Assert.Equal(ClaimCategories.Activity, claim.Category);
        Assert.Empty(view.Outcomes);
        var trace = h.Outcomes.Trace(Tenant, Relationship, claim.ClaimId)!;
        Assert.Equal(2, trace.WorkItems.Count);
        Assert.Equal(["ev"], trace.Evidence);
    }

    [Fact]
    public async Task AnAgentStatedFigureIsLabelledAndAClaimWithoutWorkOrEvidenceIsWithheld()
    {
        var h = new Harness();
        var artifact = await h.Decided("""{"post":"p"}""");
        var work = Guid.NewGuid();
        h.Timeline.Ingest(
            Tenant,
            Relationship,
            Event(work, "COMPLETED", artifact) with
            {
                EvidenceRefs = ["ev"],
            }
        );
        h.Outcomes.RecordAgentClaim(
            Tenant,
            Relationship,
            Claim("reach", "Reach rose by 40 percent", ClaimCategories.Activity, 40, [work], ["ev"])
        );
        h.Outcomes.RecordAgentClaim(
            Tenant,
            Relationship,
            Claim("ghost", "Reach doubled", ClaimCategories.Activity, 2, [Guid.NewGuid()], ["ev"])
        );
        h.Outcomes.RecordAgentClaim(
            Tenant,
            Relationship,
            Claim("bare", "Many enquiries", ClaimCategories.Activity, 9, [work], [])
        );

        var view = h.Outcomes.Read(Tenant, Relationship);

        var stated = Assert.Single(view.AgentStated);
        Assert.Equal("AGENT_STATED", stated.Derivation);
        Assert.Equal(RealWorkOutcomeService.AgentStatedLabel, stated.Label);
        Assert.Equal(2, view.WithheldClaims);
        Assert.DoesNotContain(view.Outcomes, claim => claim.ClaimId == "reach");
    }

    [Fact]
    public async Task ABusinessOutcomeReadsNotMeasurableYetAndNeverShowsANumber()
    {
        var h = new Harness();
        var artifact = await h.Decided("""{"post":"p"}""");
        var work = Guid.NewGuid();
        h.Timeline.Ingest(
            Tenant,
            Relationship,
            Event(work, "COMPLETED", artifact) with
            {
                EvidenceRefs = ["ev"],
            }
        );
        h.Outcomes.RecordAgentClaim(
            Tenant,
            Relationship,
            Claim("leads", "Qualified enquiries", ClaimCategories.Outcome, 12, [work], ["ev"])
        );

        var view = h.Outcomes.Read(Tenant, Relationship);

        var slot = Assert.Single(view.NotMeasurableYet);
        Assert.Equal("Not measurable yet", slot.Text);
        Assert.All(view.AgentStated, claim => Assert.Null(claim.Value));
        Assert.Empty(view.Outcomes);
    }

    [Fact]
    public void TheLedgerIsIdempotentPerKeyAndConflictsOnADifferentPayload()
    {
        var ledger = new InMemoryRealWorkLedger();
        var now = DateTimeOffset.UtcNow;
        var first = ledger.Append(Tenant, Relationship, "TIMELINE", "k1", Json("""{"a":1}"""), now);

        Assert.Equal(
            first.Sequence,
            ledger.Append(Tenant, Relationship, "TIMELINE", "k1", Json("""{"a":1}"""), now).Sequence
        );
        Assert.Equal(
            "REAL_WORK_IDEMPOTENCY_CONFLICT",
            Assert
                .Throws<RealWorkConflictException>(() =>
                    ledger.Append(Tenant, Relationship, "TIMELINE", "k1", Json("""{"a":2}"""), now)
                )
                .Code
        );
        Assert.Equal(
            2,
            ledger.Append(Tenant, Relationship, "TIMELINE", "k2", Json("""{"a":3}"""), now).Sequence
        );
    }

    private static AgentClaimInput Claim(
        string id,
        string text,
        string category,
        decimal value,
        Guid[] work,
        string[] evidence
    ) => new(id, id, text, category, value, "COUNT", DateTimeOffset.UtcNow, work, evidence);

    private static ArtifactProposal Proposal(string content) =>
        new("CAMPAIGN_BRIEF", Json(content), "A plain summary.");

    private static TimelineEventInput Event(Guid work, string state, ArtifactView artifact) =>
        new(
            Guid.NewGuid(),
            work,
            "CONTENT_ITEM",
            state,
            DateTimeOffset.UtcNow,
            artifact.ArtifactId,
            artifact.Digest
        );

    private static JsonElement Json(string text)
    {
        using var document = JsonDocument.Parse(text);
        return document.RootElement.Clone();
    }

    private sealed class Harness
    {
        public IRealWorkLedger Ledger { get; } = new InMemoryRealWorkLedger();
        public RecordingGateway Gateway { get; } = new();
        public RealWorkArtifactService Artifacts { get; }
        public RealWorkDecisionService Decisions { get; }
        public RealWorkTimelineService Timeline { get; }
        public RealWorkOutcomeService Outcomes { get; }

        public Harness()
        {
            Artifacts = new RealWorkArtifactService(Ledger, TimeProvider.System);
            Decisions = new RealWorkDecisionService(
                Ledger,
                Artifacts,
                Gateway,
                TimeProvider.System
            );
            Timeline = new RealWorkTimelineService(Ledger, Decisions, TimeProvider.System);
            Outcomes = new RealWorkOutcomeService(Ledger, Timeline, TimeProvider.System);
        }

        public Task<DecisionView> Approve(ArtifactView artifact, Guid? relationship = null) =>
            Decisions.ApproveAsync(
                Tenant,
                relationship ?? Relationship,
                Actor,
                "agent",
                artifact.ArtifactId,
                artifact.Digest,
                Guid.NewGuid(),
                7,
                CancellationToken.None
            );

        public Task<DecisionView> Scope(ArtifactView artifact, Guid? relationship = null) =>
            Decisions.ConfirmScopeAsync(
                Tenant,
                relationship ?? Relationship,
                Actor,
                "agent",
                artifact.ArtifactId,
                artifact.Digest,
                Guid.NewGuid(),
                7,
                CancellationToken.None
            );

        public async Task<ArtifactView> Decided(string content, Guid? relationship = null)
        {
            var scope = relationship ?? Relationship;
            var artifact = Artifacts.Propose(Tenant, scope, Proposal(content));
            await Approve(artifact, scope);
            await Scope(artifact, scope);
            return Artifacts.Get(Tenant, scope, artifact.ArtifactId)!;
        }
    }

    private sealed class FixedVersions(long value) : IDecisionSpaceVersions
    {
        public long Value { get; set; } = value;

        public long? Current(Guid tenantId, Guid relationshipId) => Value;
    }

    private sealed class RecordingGateway : IRelationshipConstitutionalGateway
    {
        public bool Deny { get; set; }
        public List<string> ActionTypes { get; } = [];

        public Task<Guid> AuthorizeAndRecordAsync(
            Guid tenantId,
            Guid relationshipId,
            string professionalType,
            string actionType,
            Guid correlationId,
            object actionParameters,
            CancellationToken cancellationToken
        )
        {
            if (Deny)
                throw new ConstitutionalActionDeniedException("denied");
            ActionTypes.Add(actionType);
            return Task.FromResult(Guid.NewGuid());
        }
    }
}
