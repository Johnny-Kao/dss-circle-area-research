# ASTM SCD DSS: OIR circle overlap test scenario

## Overview

Tests the DSS operational intent reference search API when a small query circle
overlaps a larger registered circular operational intent reference (OIR) close
to its boundary.

The scenario constructs a circular OIR inside the provided
`PlanningAreaResource` and searches with a 1 m circle overlapping its edge.
When possible, the circles are placed on opposite sides of an actual spatial
indexing boundary. A smaller circle contained inside the OIR is also queried.
Both searches must discover the OIR when their altitude and time intervals
overlap.

The planning area must provide sufficient room to accommodate the circles
and a positive altitude interval in W84 meters. The scenario selects an
altitude interval strictly inside the supplied limits (using a 90 m span
when one or both limits are absent). The locations are derived from the
supplied planning area; no fixed geographic coordinates are required.

When the specialized spatial-index boundary layout is unavailable but a valid
boundary-overlap layout exists, the scenario executes the latter and records
`fixture_type: general_overlap`. This still checks the ASTM positive-search
requirement, but does not claim to exercise the specialized regression case.
If no valid boundary-overlap layout exists, or the altitude reference is
unsupported, the scenario records a test-inapplicable note and makes no DSS
conformance assertion. Such a run must not count as
a passing Red/Green regression.

## Resources

### dss

Client to a DSS instance with ASTM F3548-21 Strategic Coordination permission,
used to create, search, and delete operational intent references.

### id_generator

An `IDGeneratorResource` supplying a dedicated OIR ID.

### planning_area

A `PlanningAreaResource` specifying where to place the test circles.

## Setup test case

### Clear previous test OIR test step

Remove an OIR left by a previous run, if it exists.

#### 🛑 Operational intent references can be queried by ID check

Retrieving an OIR by ID must succeed or return 404 when absent;
otherwise **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)** is violated.

#### 🛑 Operational intent reference removed check

An OIR must be removable by ID and correct OVN under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Discover an OIR through an overlapping circle test case

### Create large circular OIR test step

Create one accepted circular OIR (radius selected to fit the test geometry)
with a defined time and altitude range.

#### 🛑 Create operational intent reference query succeeds check

Valid OIR creation must succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Boundary overlap is discoverable test step

A 1 m search circle that overlaps the boundary of the registered OIR
must discover the OIR when its time and altitude intervals also overlap.

#### ⚠️ Boundary overlap is discoverable check

The overlapping reference must be discovered under
**[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Ordinary contained circle is discoverable test step

A smaller circle entirely contained within the registered OIR must
discover the OIR.

#### 🛑 Ordinary contained circle is discoverable check

The overlapping reference must be discovered under
**[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Delete large circular OIR test step

Remove the created OIR after the searches.

#### 🛑 Delete operational intent reference query succeeds check

Deleting an OIR with the correct OVN must succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Cleanup

### Clean up test OIR test step

Remove the known OIR ID on failure or early termination.

#### ⚠️ Operational intent references can be queried by ID check

The DSS should return the reference or 404 for an absent reference under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Operational intent reference removed check

An OIR must be removable using the correct OVN under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.
