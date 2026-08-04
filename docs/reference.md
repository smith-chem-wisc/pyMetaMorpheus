# API reference

Auto-generated from the source. Everything here is importable straight from the top-level package
(`import pymetamorpheus as mm`).

## Verbs

The high-level entry points — each runs one task (or, for `pipeline`/`run_toml`, several) and returns a
[`RunResult`](#results).

::: pymetamorpheus.search
::: pymetamorpheus.calibrate
::: pymetamorpheus.gptmd
::: pymetamorpheus.glyco_search
::: pymetamorpheus.xl_search
::: pymetamorpheus.pipeline
::: pymetamorpheus.run_toml

## Introspection

::: pymetamorpheus.available_parameters

## Task builders

Return a [`Task`](#pymetamorpheus.Task) without running it, so you can compose custom pipelines and
pass them to [`pipeline`](#pymetamorpheus.pipeline).

::: pymetamorpheus.make_search_task
::: pymetamorpheus.make_calibration_task
::: pymetamorpheus.make_gptmd_task
::: pymetamorpheus.make_glyco_search_task
::: pymetamorpheus.make_xl_search_task
::: pymetamorpheus.task_from_toml
::: pymetamorpheus.Task

## Results

::: pymetamorpheus.RunResult
::: pymetamorpheus.TaskResult

## Errors

::: pymetamorpheus.PyMetaMorpheusError
::: pymetamorpheus.UsageError
::: pymetamorpheus.RunError
::: pymetamorpheus.MetaMorpheusNotFoundError
