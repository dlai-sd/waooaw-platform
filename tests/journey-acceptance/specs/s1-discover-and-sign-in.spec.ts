// Implements: validation/acceptance/plans/slice-1-discover-to-connect.v1.yaml steps S1, S2
// Constitutional basis: C-059 (Implementation Traceability), C-023 (Evidence First)
import { reading, unreadable } from "../lib/claim.ts";
import { pick } from "../lib/platform.ts";
import { acceptanceStep } from "./support/acceptance.ts";
import { bodyText, scriptVisibleState, signIn, signOut } from "./support/ui.ts";
import { scanText } from "../lib/guards.ts";

const PRICE = /(?:₹|INR)\s?[\d,]+(?:\.\d+)?/u;

acceptanceStep("S1", { covers: ["AE-01-S02", "PG-02", "PG-09", "WC107-R009"] }, async ({ visitor, run }) => {
  const page = await visitor();
  await page.goto("/professionals");
  const text = await bodyText(page);
  const shown = run.agent.offer.test(text);
  const priceShown = PRICE.test(text);
  const discovery = await page.request.get(`${run.profile.origins.api}/api/v1/professionals?outcome=${encodeURIComponent("grow my business with marketing")}`, {
    failOnStatusCode: false,
  });
  const listed = discovery.ok() ? await discovery.text() : "";
  return {
    reached: "L1",
    readings: {
      "S1-C1": [
        reading("W1", true, shown && priceShown, shown ? (priceShown ? "offer and price shown" : "offer shown, no price on the card") : "offer card not found"),
        // The disclosure price is served only with a bearer token the harness must not hold; the public discovery route carries no price.
        discovery.ok() && run.agent.offer.test(listed)
          ? unreadable("W2", "the public discovery route lists the offer but no customer-reachable route exposes the disclosure price, rights or limits")
          : unreadable("W2", "the public discovery route did not list the offer"),
      ],
    },
  };
});

acceptanceStep("S2", { covers: ["PG-03", "WC107-R001", "WC107-R004", "WC107-R005", "WC107-R017"] }, async ({ customer, run }) => {
  const { page, context } = await customer("A");
  const account = async (): Promise<unknown> => pick((await run.platform(page, "/api/identity/account")).json, ["id", "subject", "membershipId", "accountId"]);
  const firstIdentity = await account();
  const session = await run.platform(page, "/api/auth/session");
  const exposed = scanText(JSON.stringify(session.json ?? {})).length + scanText(await scriptVisibleState(page)).length;
  await signOut(page);
  const customerA = run.state.customers.A;
  if (customerA === undefined) {
    throw new Error("customer A is not provisioned");
  }
  await signIn(page, customerA);
  const resumed = !page.url().includes("/register");
  const secondIdentity = await account();
  const sameAccount = firstIdentity !== undefined && firstIdentity === secondIdentity;
  await run.saveSession(context, "A");
  return {
    reached: "L3",
    readings: {
      "S2-C1": [
        reading("W1", { resumed: true, tokenReachable: false }, { resumed, tokenReachable: exposed > 0 }, "after sign out and in again"),
        firstIdentity === undefined
          ? unreadable("W2", "the identity account route did not expose a stable account identifier")
          : reading("W2", true, sameAccount, "same account identifier after the second sign in"),
      ],
    },
  };
});
