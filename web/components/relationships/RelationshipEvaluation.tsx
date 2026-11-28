import {
  CalendarDays,
  CircleDollarSign,
  FlaskConical,
  MessageSquareText,
  Settings2,
  UserRoundCheck,
} from 'lucide-react';
import type { RelationshipEvaluationProjection } from '@/lib/api/relationships';
import Link from 'next/link';

const display = (value: string) => value.replaceAll('_', ' ').toLowerCase();
const dayMs = 86_400_000;

// The countdown comes from the trial's own start and end dates (the billing owner's trial), never a fixed length.
export function trialCountdown(startsAt: string, expiresAt: string, now: number = Date.now()) {
  const start = new Date(startsAt).getTime();
  const end = new Date(expiresAt).getTime();
  const totalDays = Math.max(1, Math.round((end - start) / dayMs));
  const daysLeft = Math.min(totalDays, Math.max(0, Math.ceil((end - now) / dayMs)));
  return {
    totalDays,
    daysLeft,
    dayNumber: Math.min(totalDays, Math.max(1, totalDays - daysLeft + 1)),
    ended: now >= end,
  };
}

export function RelationshipEvaluation({ evaluation }: { evaluation: RelationshipEvaluationProjection }) {
  const trialStart = evaluation.trial ? new Date(evaluation.trial.startsAt) : null;
  const trialEnd = evaluation.trial ? new Date(evaluation.trial.expiresAt) : null;
  const countdown = evaluation.trial ? trialCountdown(evaluation.trial.startsAt, evaluation.trial.expiresAt) : null;
  const totalDays = countdown?.totalDays ?? 14;

  return (
    <section className="evaluation-journey" aria-labelledby="evaluation-journey-title">
      <div className="evaluation-heading">
        <p className="section-label">Evaluation journey</p>
        <h2 id="evaluation-journey-title">Inspect, demonstrate, then configure</h2>
      </div>
      <ol className="journey-rail" aria-label="Discover to configure progress">
        {['Discover', 'Disclosure', 'Interview', 'Context', `${totalDays}-day trial`, 'Configure'].map(
          (step, index) => (
            <li className={index < 2 || evaluation.interviewState !== 'NOT_STARTED' ? 'complete' : ''} key={step}>
              <span>{index + 1}</span>
              {step}
            </li>
          )
        )}
      </ol>

      <div className="evaluation-panels">
        <article>
          <h3>
            <MessageSquareText aria-hidden="true" size={20} /> Interview
          </h3>
          <p>
            Ask serious-buyer questions in the conversation. Answers must separate facts, inference, recommendation, and
            limitations.
          </p>
          <a href="#relationship-conversation">Continue interview</a>
        </article>
        <article>
          <h3>
            <UserRoundCheck aria-hidden="true" size={20} /> Confirmed context
          </h3>
          {evaluation.context.length ? (
            <dl>
              {evaluation.context.map((item) => (
                <div key={item.payloadReference}>
                  <dt>{display(item.fieldType)}</dt>
                  <dd>{typeof item.value === 'string' ? item.value : JSON.stringify(item.value)}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p>No context has been confirmed.</p>
          )}
          {evaluation.nextContextQuestion && (
            <p className="next-question">
              <strong>Next question</strong>
              {evaluation.nextContextQuestion}
            </p>
          )}
        </article>
        <article className="trial-plan">
          <h3>
            <CalendarDays aria-hidden="true" size={20} /> {totalDays}-day demonstration
          </h3>
          {evaluation.trial && trialStart && trialEnd && countdown ? (
            <>
              <div className="trial-meter">
                <span style={{ width: `${(countdown.dayNumber / countdown.totalDays) * 100}%` }} />
              </div>
              <p>
                <strong>
                  {countdown.ended
                    ? 'Your trial has ended'
                    : countdown.daysLeft === 1
                      ? '1 day left'
                      : `${countdown.daysLeft} days left`}
                </strong>{' '}
                · {display(evaluation.trial.status)} · {countdown.ended ? 'ended' : 'ends'}{' '}
                <time dateTime={evaluation.trial.expiresAt}>{trialEnd.toLocaleDateString('en-IN')}</time>
              </p>
              {countdown.totalDays === 14 ? (
                <div className="trial-phases">
                  <span>
                    Days 1–3
                    <br />
                    <small>Understand and plan</small>
                  </span>
                  <span>
                    Days 4–10
                    <br />
                    <small>Skill demonstrations</small>
                  </span>
                  <span>
                    Days 11–14
                    <br />
                    <small>Review and configure</small>
                  </span>
                </div>
              ) : null}
              <p className="quota-state">
                <CircleDollarSign aria-hidden="true" size={17} /> Trial quota is unavailable from its billing owner. No
                estimate is shown.
              </p>
              {countdown.ended ? (
                <p>
                  <Link className="primary-command" href="/marketplace">
                    Hire your agent to keep it working
                  </Link>
                </p>
              ) : (
                <p className="connection-hint">
                  Some skills work through your social accounts. Connect them in{' '}
                  <Link href="/connections">Connections</Link> when you are ready. Until then your agent works in
                  practice mode during the trial: nothing is published and nothing is spent.
                </p>
              )}
            </>
          ) : (
            <p>Trial has not started. No countdown or entitlement is assumed.</p>
          )}
        </article>
        <article>
          <h3>
            <FlaskConical aria-hidden="true" size={20} /> Skill demonstrations
          </h3>
          {evaluation.skills.length ? (
            <ul className="decision-list">
              {evaluation.skills.map((skill) => (
                <li key={skill.configurationId}>
                  <span>
                    <strong>{display(skill.skillId)}</strong>
                    <small>{skill.applicabilityReason ?? display(skill.applicability)}</small>
                  </span>
                  <b>{display(skill.status)}</b>
                </li>
              ))}
            </ul>
          ) : (
            <p>Skill decisions have not been proposed.</p>
          )}
        </article>
        <article>
          <h3>
            <Settings2 aria-hidden="true" size={20} /> Configuration decisions
          </h3>
          {evaluation.goals.length ? (
            <ul className="decision-list">
              {evaluation.goals.map((goal) => (
                <li key={goal.goalId}>
                  <span>
                    <strong>{goal.goal}</strong>
                    <small>
                      {goal.measure} · review every {goal.reviewCadenceMonths} months
                    </small>
                  </span>
                  <b>{display(goal.status)}</b>
                </li>
              ))}
            </ul>
          ) : (
            <p>Goals and measures have not been proposed.</p>
          )}
          {evaluation.decisionSpace ? (
            <dl className="decision-space">
              <div>
                <dt>Budget ceiling</dt>
                <dd>
                  {new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(
                    evaluation.decisionSpace.budgetCeilingInrPaise / 100
                  )}
                </dd>
              </div>
              <div>
                <dt>Decision Space</dt>
                <dd>Version {evaluation.decisionSpace.version}</dd>
              </div>
              <div>
                <dt>Stop conditions</dt>
                <dd>{evaluation.decisionSpace.stopConditions.length}</dd>
              </div>
            </dl>
          ) : (
            <p>Budget, authority, and stop conditions remain undecided.</p>
          )}
        </article>
      </div>
    </section>
  );
}
