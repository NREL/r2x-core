# Changelog

## [0.4.0](https://github.com/NREL/r2x-core/compare/v0.3.1...v0.4.0) (2026-01-21)


### ⚠ BREAKING CHANGES

* Standardizing API for plugins and AST-discoverability. ([#76](https://github.com/NREL/r2x-core/issues/76))

### Refactoring

* add new rule filter and update time series transfer ([#72](https://github.com/NREL/r2x-core/issues/72)) ([334b817](https://github.com/NREL/r2x-core/commit/334b8170361c03e09d599445309f0ce55cf252de))
* **core:** simplify codebase and remove deprecated modules ([1348f04](https://github.com/NREL/r2x-core/commit/1348f042e613dcc69efafc35527e47ae0884bfdf))
* **plugin:** clarify plugin system and public API ([1348f04](https://github.com/NREL/r2x-core/commit/1348f042e613dcc69efafc35527e47ae0884bfdf))
* Standardizing API for plugins and AST-discoverability. ([#76](https://github.com/NREL/r2x-core/issues/76)) ([1348f04](https://github.com/NREL/r2x-core/commit/1348f042e613dcc69efafc35527e47ae0884bfdf))


### Documentation

* **structure:** restructure and significantly expand documentation ([1348f04](https://github.com/NREL/r2x-core/commit/1348f042e613dcc69efafc35527e47ae0884bfdf))


### CI/CD

* **docs:** enforce documentation and encoding standards ([1348f04](https://github.com/NREL/r2x-core/commit/1348f042e613dcc69efafc35527e47ae0884bfdf))


### Build

* **deps-dev:** bump myst-parser from 3.0.1 to 4.0.1 ([#67](https://github.com/NREL/r2x-core/issues/67)) ([b9f7223](https://github.com/NREL/r2x-core/commit/b9f72233bd6470c5cb56567ea00f1f2d0841cd40))
* **deps-dev:** bump pytest from 9.0.1 to 9.0.2 ([#66](https://github.com/NREL/r2x-core/issues/66)) ([f330b78](https://github.com/NREL/r2x-core/commit/f330b78eca8539f3a109d243e4af2d6eea116882))
* **deps:** bump actions/download-artifact from 6 to 7 ([#70](https://github.com/NREL/r2x-core/issues/70)) ([354f967](https://github.com/NREL/r2x-core/commit/354f967985e984afa24d40df2735c85bb65df21d))
* **deps:** bump actions/upload-artifact from 5 to 6 ([#69](https://github.com/NREL/r2x-core/issues/69)) ([c1359d5](https://github.com/NREL/r2x-core/commit/c1359d52f2e9287852c4db51db97263a4ff2e47c))
* **deps:** stabilize dependencies and build configuration ([1348f04](https://github.com/NREL/r2x-core/commit/1348f042e613dcc69efafc35527e47ae0884bfdf))
* **tooling:** modernize tooling, type checking, and CI ([1348f04](https://github.com/NREL/r2x-core/commit/1348f042e613dcc69efafc35527e47ae0884bfdf))


### Tests

* **coverage:** increase coverage and strengthen correctness guarantees ([1348f04](https://github.com/NREL/r2x-core/commit/1348f042e613dcc69efafc35527e47ae0884bfdf))

## [0.3.1](https://github.com/NREL/r2x-core/compare/v0.3.0...v0.3.1) (2025-12-23)

### Bug Fixes

- Sorting of rules without name and dependency ([#68](https://github.com/NREL/r2x-core/issues/68)) ([52df559](https://github.com/NREL/r2x-core/commit/52df5598e97aba56620d0795da900ca8884f7e60))

## [0.3.0](https://github.com/NREL/r2x-core/compare/v0.2.4...v0.3.0) (2025-12-13)

### Features

- add new rules to filter starbuses in s2p translation ([#64](https://github.com/NREL/r2x-core/issues/64)) ([7c81ea1](https://github.com/NREL/r2x-core/commit/7c81ea168b9ba5eeb734c31f62069c5b6f4be2d6))

## [0.2.4](https://github.com/NREL/r2x-core/compare/v0.2.3...v0.2.4) (2025-12-09)

### Bug Fixes

- Adding more logging and deduplication logic for time series translations ([#62](https://github.com/NREL/r2x-core/issues/62)) ([841fbdc](https://github.com/NREL/r2x-core/commit/841fbdc23265b6b870195c2198d16ea23f69f39b))

## [0.2.3](https://github.com/NREL/r2x-core/compare/v0.2.2...v0.2.3) (2025-11-29)

### Bug Fixes

- H5_reader was not respecting reader_kwargs for index names ([#56](https://github.com/NREL/r2x-core/issues/56)) ([5bf709a](https://github.com/NREL/r2x-core/commit/5bf709ab1c8ae324e7841e84defec9c1e4e1110a))

## [0.2.2](https://github.com/NREL/r2x-core/compare/v0.2.1...v0.2.2) (2025-11-29)

### Bug Fixes

- Pydantic validation errors on DataFile errors were not propogated correctly. ([#53](https://github.com/NREL/r2x-core/issues/53)) ([2de2992](https://github.com/NREL/r2x-core/commit/2de2992d0c206cfe79e3f79011131b35b8106476))

## [0.2.1](https://github.com/NREL/r2x-core/compare/v0.2.0...v0.2.1) (2025-11-28)

### Bug Fixes

- Improving CI ([#46](https://github.com/NREL/r2x-core/issues/46)) ([6ffac6a](https://github.com/NREL/r2x-core/commit/6ffac6abcb58ccd4b0cc8fe538bb5e41cd942611))
