# Orchard Advisor fixture (declaration only)

This is a conformance fixture, not a product. It exists to prove that WAOOAW accepts a second agent from a different
profession as a new sealed image plus a declaration, and that nothing already built is rewired (WC-174 R004, R035).

It declares its own modes, menu entries, event layers and three plan levels. It has no public endpoint, holds no key,
makes no provider or model call and keeps no durable state. Its answers are fixed so that tests are deterministic.

#spec The advisor helps an orchard owner plan a season, a month and a day's tasks.
#prompt No prompts are used. The fixture returns fixed proposals.
#tools The fixture uses no tools.
#decisions Every proposal waits for the customer.
#vocabulary Season, month, task, sowing, mandi day.
#plan A season plan becomes monthly plans, which become daily tasks.
#outcome Outcomes are recorded by the customer.
#billing The fixture is not sold.
#degradation If a feed is unavailable the fixture says so and proposes nothing.
