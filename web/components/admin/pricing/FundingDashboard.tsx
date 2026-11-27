// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-08
// Constitutional basis: C-023, C-059, C-063, C-088

import { formatInr } from '@/lib/pricing-admin-client';
import type { ComponentCost, FundingDashboard as Funding, MarginDashboard as Margin } from '@/lib/pricing-admin-types';

type Props = { funding: Funding | null; margin: Margin | null; from: string; to: string };

const toleranceText: Record<ComponentCost['toleranceState'], string> = {
  WITHIN_TOLERANCE: 'Within tolerance',
  ALERT: 'Alert: cost is drifting above the recipe',
  EXCEEDED: 'Exceeded: cost is above the tolerated limit',
};

function Empty({ label }: { label: string }) {
  return <p className="workbench-hint">{label}</p>;
}

function SpendTable({
  caption,
  head,
  rows,
}: { caption: string; head: string; rows: { label: string; paise: number }[] }) {
  if (rows.length === 0) return <Empty label={`No ${caption.toLowerCase()} in this period.`} />;
  return (
    <table aria-label={caption}>
      <thead>
        <tr>
          <th scope="col">{head}</th>
          <th scope="col">Spent</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.label}>
            <th scope="row">{row.label}</th>
            <td>{formatInr(row.paise)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ComponentCostTable({ rows }: { rows: ComponentCost[] }) {
  if (rows.length === 0) return <Empty label="No component cost has been recorded in this period." />;
  return (
    <table aria-label="Actual against recipe cost">
      <thead>
        <tr>
          <th scope="col">Component</th>
          <th scope="col" title="What the price assumed this component costs">
            Recipe cost
          </th>
          <th scope="col" title="What was really spent in this period">
            Actual cost
          </th>
          <th scope="col" title="The margin left when the actual cost is used instead of the recipe cost">
            Implied margin
          </th>
          <th scope="col" title="Whether the actual cost stays within the allowed gap from the recipe cost">
            Tolerance
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.componentId}>
            <th scope="row">{row.componentId}</th>
            <td>{formatInr(row.recipeCostPaise)}</td>
            <td>{formatInr(row.actualCostPaise)}</td>
            <td>{row.impliedMarginPercent.toFixed(1)}%</td>
            <td>{toleranceText[row.toleranceState]}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function FundingDashboard({ funding, margin, from, to }: Props) {
  return (
    <div className="workbench-stack">
      <form aria-label="Reporting period" className="workbench-form" method="get">
        <label htmlFor="period-from">From</label>
        <input defaultValue={from} id="period-from" name="from" type="date" />
        <label htmlFor="period-to">To</label>
        <input defaultValue={to} id="period-to" name="to" type="date" />
        <button className="secondary-link" type="submit">
          Show period
        </button>
      </form>

      {funding === null ? (
        <p className="workbench-message workbench-message-error" role="alert">
          <strong>Error:</strong> The funding report could not be loaded. Try again shortly.
        </p>
      ) : (
        <section aria-label="Funding" className="workbench-section">
          <h2>Funding</h2>
          <dl>
            <dt>Cost per lead</dt>
            <dd>{formatInr(funding.costPerLeadPaise)}</dd>
            <dt>Cost per conversation</dt>
            <dd>{formatInr(funding.costPerConversationPaise)}</dd>
            <dt>Trial to hire</dt>
            <dd>
              {funding.trialToHire.hires} hires from {funding.trialToHire.trials} trials (
              {funding.trialToHire.conversionPercent.toFixed(1)}%)
            </dd>
            <dt>Live margin breaches</dt>
            <dd>{funding.liveMarginBreaches}</dd>
          </dl>
          <h3>Spend by account class</h3>
          <SpendTable
            caption="Spend by account class"
            head="Account class"
            rows={funding.spendByAccountClass.map((row) => ({ label: row.accountClass, paise: row.spentPaise }))}
          />
          <h3>Spend by tenant</h3>
          <SpendTable
            caption="Spend by tenant"
            head="Tenant"
            rows={funding.spendByTenant.map((row) => ({ label: row.tenantRef, paise: row.spentPaise }))}
          />
          <h3>Spend by campaign</h3>
          <SpendTable
            caption="Spend by campaign"
            head="Campaign"
            rows={funding.spendByCampaign.map((row) => ({ label: row.campaignRef, paise: row.spentPaise }))}
          />
          <h3>Spend by lead (pseudonymous)</h3>
          <SpendTable
            caption="Spend by lead"
            head="Lead reference"
            rows={funding.leadSpend.map((row) => ({ label: row.leadRef, paise: row.spentPaise }))}
          />
          <h3>Grant consumption</h3>
          {funding.grantConsumption.length === 0 ? (
            <Empty label="No grants have been consumed in this period." />
          ) : (
            <table aria-label="Grant consumption">
              <thead>
                <tr>
                  <th scope="col">Grant</th>
                  <th scope="col">Consumed</th>
                  <th scope="col">Granted</th>
                </tr>
              </thead>
              <tbody>
                {funding.grantConsumption.map((row) => (
                  <tr key={`${row.grantKind}:${row.agentType}:${row.agentVersion}`}>
                    <th scope="row">
                      {row.grantKind} {row.agentType} {row.agentVersion}
                    </th>
                    <td>{formatInr(row.consumedPaise)}</td>
                    <td>{formatInr(row.grantedPaise)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <h3>Actual against recipe cost</h3>
          <ComponentCostTable rows={funding.componentCost} />
          <h3>Exhaustion and top-up events</h3>
          {funding.events.length === 0 ? (
            <Empty label="No exhaustion or top-up events in this period." />
          ) : (
            <ul aria-label="Events" className="workbench-plain-list">
              {funding.events.map((event) => (
                <li key={event.eventKind}>
                  {event.eventKind === 'EXHAUSTION' ? 'Allowance exhausted' : 'Top-ups bought'}: {event.count}
                </li>
              ))}
            </ul>
          )}
          <h3>Breakers</h3>
          {funding.breakers.length === 0 ? (
            <Empty label="No breaker state is reported." />
          ) : (
            <ul aria-label="Breakers" className="workbench-plain-list">
              {funding.breakers.map((breaker) => (
                <li key={breaker.breaker}>
                  {breaker.breaker}: {breaker.state.replace('_', ' ').toLowerCase()}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {margin === null ? (
        <p className="workbench-message workbench-message-error" role="alert">
          <strong>Error:</strong> The margin report could not be loaded. Try again shortly.
        </p>
      ) : (
        <section aria-label="Margin" className="workbench-section">
          <h2>Margin</h2>
          {margin.packages.length === 0 ? (
            <Empty label="No packages are effective yet." />
          ) : (
            <table aria-label="Package margins">
              <thead>
                <tr>
                  <th scope="col">Package</th>
                  <th scope="col">Price including GST</th>
                  <th scope="col">Base price</th>
                  <th scope="col">Cost floor</th>
                  <th scope="col">Margin</th>
                  <th scope="col">Minimum margin</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {margin.packages.map((row) => (
                  <tr key={row.packageVersionId}>
                    <th scope="row">{row.subjectKey}</th>
                    <td>{formatInr(row.priceInclGstPaise)}</td>
                    <td>{formatInr(row.basePricePaise)}</td>
                    <td>{formatInr(row.costFloorPaise)}</td>
                    <td>{row.marginPercent.toFixed(1)}%</td>
                    <td>{row.minimumMarginPercent.toFixed(1)}%</td>
                    <td>
                      {row.marginPercent < row.minimumMarginPercent
                        ? 'Below the minimum margin'
                        : 'Meets the minimum margin'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <h3>Component cost</h3>
          <ComponentCostTable rows={margin.componentCost} />
        </section>
      )}
    </div>
  );
}
