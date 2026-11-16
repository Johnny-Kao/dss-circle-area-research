# ASTM SCD DSS: Circular OIR overlap search test scenario

## Overview

Tests the DSS operational intent reference search API when a small circular query genuinely overlaps a larger registered circular operational intent reference (OIR) close to its boundary.

The scenario places four circular OIRs, one at a time, near S2 cell boundaries in four different source cells, selecting positions where an inscribed reference footprint remains in the original cell within the configured PlanningAreaResource. A 1 m query circle overlaps each 100–200 m OIR with a small positive overlap. Their altitude and time ranges also overlap. The OIR must be returned because the 4D query intersects it. Additional search results are permitted. The scenario also performs an ordinary contained-circle query as a positive control.

The `PlanningAreaResource` must have enough horizontal and vertical room for four distinct source-cell boundary placements. If fewer than four independent placements can be found, the test configuration is unsuitable for this scenario rather than indicating a DSS conformance failure.

## Resources

### dss

Client to a DSS instance with ASTM F3548-21 Strategic Coordination permission, used to create, search for, and delete operational intent references.

### id_generator

An `IDGeneratorResource` supplying the test OIR ID.

### planning_area

A `PlanningAreaResource` specifying where to place the test circles.

## Setup test case

### Clear previous test OIR test step

Remove an OIR left by a previous run, if present.

#### 🛑 Operational intent references can be queried by ID check

The reference must either be returned or be absent under **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Operational intent reference removed check

Removing a previously existing reference must succeed under **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Overlapping circular OIR is discoverable test case

### Create circular OIR test step

Create four accepted circular OIRs (100–200 m radius), one at a time, with valid time and altitude bounds.

#### 🛑 Create operational intent reference query succeeds check

Creating the OIR must succeed under **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Discover boundary-overlapping OIR test step

A 1 m query circle genuinely overlaps the registered circular OIR near its boundary. Their time and altitude intervals also overlap.

#### ⚠️ Boundary overlap is discoverable check

The overlapping reference must be discovered under **[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Ordinary contained circle discovers OIR test step

An ordinary circular query contained well inside the registered OIR must discover the OIR when the time and altitude intervals also overlap.

#### 🛑 Ordinary contained circle discovers OIR check

The overlapping reference must be discovered under **[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Delete circular OIR test step

Delete the registered OIR using its returned OVN.

#### 🛑 Delete operational intent reference query succeeds check

Deleting an OIR with the correct OVN must succeed under **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Cleanup

### Clean up test OIR test step

Delete any remaining OIR after an error or early termination.

#### ⚠️ Operational intent references can be queried by ID check

The reference should be returned or absent under **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Operational intent reference removed check

Deleting a remaining OIR with the correct OVN should succeed under **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.
