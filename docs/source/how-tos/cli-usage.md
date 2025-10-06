# ... list available plugins

```bash
# List all registered plugins
r2x list

# Output:
# Parsers:
#   switch - Switch model parser
#   plexos - PLEXOS model parser
#   reeds - ReEDS model parser
#
# Exporters:
#   plexos - PLEXOS model exporter
#   sienna - Sienna model exporter
#
# System Modifiers:
#   add_storage - Add battery storage to all buses
#   scale_generation - Scale generation capacity
#   emission_cap - Add emission constraint
#
# Filters:
#   rename_columns - Rename DataFrame columns
#   filter_by_year - Filter data by year

# List only parsers
r2x list --type parser

# List only modifiers
r2x list --type modifier
```

# ... understand the translation workflow

```bash
# The r2x CLI follows this workflow:
# 1. READ: Parse source model → Canonical System (via parser.build_system())
# 2. RUN: Apply modifiers → Modified System (including model conversions)
# 3. WRITE: Export System → Target model files (via exporter.export())

# Example: Switch → PLEXOS translation
# Step-by-step (explicit):
r2x read switch ./data/switch -o switch_system.json       # Canonical System
r2x run switch_to_plexos < switch_system.json -o mapped.json  # Model conversion
r2x write plexos ./output < mapped.json                    # Export to files

# Same workflow (implicit via pipes):
r2x read switch ./data/switch | \
  r2x run switch_to_plexos | \
  r2x write plexos ./output

# Without model-specific conversion (if formats are compatible):
r2x read switch ./data/switch | \
  r2x write plexos ./output

# With additional system modifications:
r2x read switch ./data/switch | \
  r2x run switch_to_plexos | \
  r2x run add_storage --capacity-mw 500 | \
  r2x run emission_cap --limit-tonnes 100000 | \
  r2x write plexos ./output
```

# ... get plugin information

```bash
# Get detailed info about a specific plugin
r2x info switch

# Output:
# Plugin: switch
# Type: Parser
# Config: SwitchConfig
# Description: Parse Switch model input files
# Parameters:
#   - input_folder (str, required)
#   - weather_year (int, default: 2012)
#   - include_reserves (bool, default: false)

# Get info about a modifier
r2x info add_storage

# Output:
# Plugin: add_storage
# Type: System Modifier
# Description: Add battery storage to all buses
# Parameters:
#   - capacity_mw (float, default: 100.0) - Storage capacity in MW
#   - duration_hours (float, default: 4.0) - Storage duration in hours

# Get info about an exporter
r2x info plexos

# Output:
# Plugin: plexos
# Type: Exporter
# Config: PlexosConfig
# Description: Export to PLEXOS model format
# Parameters:
#   - output_folder (str, required)
#   - version (str, default: "8.2")
#   - include_metadata (bool, default: true)
```

# ... read model data

```bash
# Read Switch model with default settings
r2x read switch ./data/switch

# Read with custom parameters
r2x read switch ./data/switch --weather-year 2030 --include-reserves

# Read and save to JSON file
r2x read switch ./data/switch -o system.json

# Read and display summary
r2x read switch ./data/switch --summary

# Output:
# ✓ Successfully read Switch model
# Components: 342
#   - Generators: 124
#   - Buses: 45
#   - Lines: 173
# Time series: 8,760 hours
# Data files processed: 15
```

# ... write model data

```bash
# Write system to PLEXOS format
r2x write plexos ./output/plexos < system.json

# Write with custom parameters (auto-generated from PlexosConfig fields)
r2x write plexos ./output/plexos --version 9.0 --include-metadata false < system.json

# Validate without writing
r2x write plexos ./output/plexos --dry-run < system.json

# Output:
# ✓ Validation passed
# Components to export: 342
# Files to create: 12
# Estimated size: 45 MB
```

# ... use model conversion modifiers

```bash
# Convert between model formats using registered conversion modifiers
# These modifiers map model-specific conventions and requirements

# ReEDS to PLEXOS conversion
r2x read reeds ./data/reeds | \
  r2x run reeds_to_plexos | \
  r2x write plexos ./output/plexos

# Switch to Sienna conversion
r2x read switch ./data/switch | \
  r2x run switch_to_sienna | \
  r2x write sienna ./output/sienna

# List available conversion modifiers
r2x list --type modifier --filter conversion

# Output:
# Conversion Modifiers:
#   switch_to_plexos - Map Switch components to PLEXOS format
#   reeds_to_plexos - Convert ReEDS representation to PLEXOS
#   reeds_to_sienna - Map ReEDS to Sienna/PowerSystems
#   plexos_to_sienna - Convert PLEXOS to Sienna format

# Get details about a conversion modifier
r2x info switch_to_plexos

# Output:
# Modifier: switch_to_plexos
# Type: System Modifier (Model Conversion)
# Description: Map Switch model components and conventions to PLEXOS format
# Transformations:
#   - Rename fuel types: 'naturalgas' → 'Gas', 'solar' → 'Solar'
#   - Map generator types to PLEXOS categories
#   - Convert reserve requirements to PLEXOS reserve objects
#   - Adjust time series indexing (0-based → 1-based)
# Parameters:
#   - map_reserves (bool, default: true) - Convert reserve requirements
#   - preserve_names (bool, default: false) - Keep original component names
```

# ... translate between models

```bash
# Basic translation from Switch to PLEXOS using conversion modifier
r2x read switch ./data/switch | \
  r2x run switch_to_plexos | \
  r2x write plexos ./output/plexos

# Translation with explicit parameters (auto-generated from Pydantic Fields)
r2x read switch ./data/switch --weather-year 2012 | \
  r2x run switch_to_plexos --map-reserves true | \
  r2x write plexos ./output/plexos --version 8.2

# Multi-step translation with intermediate files
r2x read switch ./data/switch -o switch_system.json
r2x run switch_to_plexos < switch_system.json -o plexos_system.json
r2x run switch_to_sienna < switch_system.json -o sienna_system.json
r2x write plexos ./output/plexos < plexos_system.json
r2x write sienna ./output/sienna < sienna_system.json

# Translation without conversion modifier (if formats are directly compatible)
r2x read switch ./data/switch | r2x write generic_format ./output

# Translation with progress output
r2x read reeds ./data/reeds --verbose | \
  r2x run reeds_to_plexos --verbose | \
  r2x write plexos ./output/plexos --verbose

# Output:
# Reading ReEDS model...
# [1/15] Processing generators.csv... ✓
# [2/15] Processing buses.csv... ✓
# ...
# Applying reeds_to_plexos modifier...
# [1/5] Mapping fuel types... ✓
# [2/5] Converting generator categories... ✓
# [3/5] Mapping timeseries... ✓
# [4/5] Adjusting reserve requirements... ✓
# [5/5] Validating PLEXOS compatibility... ✓
# Writing PLEXOS model...
# [1/12] Writing System.xml... ✓
# [2/12] Writing Generator.xml... ✓
# ...
# ✓ Translation completed successfully
```

# ... validate model conversions

```bash
# Test conversion without writing output
r2x read switch ./data/switch | \
  r2x run switch_to_plexos | \
  r2x test plexos

# Output:
# ✓ Successfully read Switch model (342 components)
# ✓ Conversion modifier applied successfully
# ✓ PLEXOS compatibility validated
# ✓ All required mappings present
# ✓ No data loss detected

# Round-trip translation to test fidelity
r2x read switch ./data/switch -o original.json
r2x run switch_to_plexos < original.json | \
  r2x write plexos ./temp
r2x read plexos ./temp -o roundtrip.json
diff <(jq -S . original.json) <(jq -S . roundtrip.json)

# Dry-run to see what would change
r2x read switch ./data/switch | \
  r2x run switch_to_plexos --dry-run

# Output:
# Would apply following transformations:
#   - Rename 124 generators (fuel type mapping)
#   - Convert 45 reserve products
#   - Adjust 8760 time series entries
#   - Map 15 generator categories
# No changes written (dry-run mode)
```

# ... apply system modifiers

```bash
# Note: Modifiers work on the canonical System representation
# Two types of modifiers:
#   1. Conversion modifiers: Map between model-specific conventions (e.g., switch_to_plexos)
#   2. Data modifiers: Transform system data (e.g., add_storage, scale_generation)

# Apply data modifier (works on any System)
r2x read switch ./data | \
  r2x run add_storage --capacity-mw 500 | \
  r2x write plexos ./output

# Apply conversion modifier + data modifiers
r2x read reeds ./data | \
  r2x run reeds_to_plexos | \
  r2x run scale_generation --factor 1.2 | \
  r2x run add_storage --capacity-mw 1000 | \
  r2x run emission_cap --limit-tonnes 50000 | \
  r2x write plexos ./output

# Order matters: conversion first, then data modifications
r2x read switch ./data | \
  r2x run switch_to_sienna | \
  r2x run add_storage --capacity-mw 500 | \
  r2x write sienna ./output

# Apply modifier with complex parameters (auto-generated from Pydantic Fields)
r2x read switch ./data | \
  r2x run add_renewable_zones \
    --zones '[{"name": "coastal", "capacity": 5000}, {"name": "desert", "capacity": 3000}]' | \
  r2x write plexos ./output

# Apply modifiers to pre-saved system
r2x run add_storage --capacity-mw 2000 < system.json -o modified.json
r2x run emission_cap --limit-tonnes 100000 < modified.json -o capped.json
r2x write plexos ./output < capped.json

r2x read switch ./data | \
  r2x run add_storage --capacity-mw 2000 -o modified.json

# Apply modifier from saved system
r2x run emission_cap --limit-tonnes 100000 < system.json > capped.json
```

# ... use data filters

```bash
# Filter time series data
r2x read switch ./data -o system.json
cat system.json | jq '.timeseries.demand' | \
  r2x filter filter_by_year --year 2030 > demand_2030.json

# Chain filters
cat data.json | \
  r2x filter rename_columns --mapping '{"old_name": "new_name"}' | \
  r2x filter filter_by_year --year '[2025, 2030, 2035]' | \
  r2x filter remove_nulls > clean_data.json

# Apply filter to CSV
r2x filter filter_by_year --year 2030 < generators.csv > generators_2030.csv
```

# ... test and validate

```bash
# Test translation path without writing output
r2x read switch ./data | r2x test plexos

# Output:
# ✓ Successfully read Switch model (342 components)
# ✓ PLEXOS exporter validation passed
# ✓ All required data present
# ✓ No data loss detected
# ✓ Translation test completed

# Test parser on sample data
r2x read my_custom_plugin ./test_data --dry-run

# Output:
# ✓ Plugin loaded successfully
# ✓ Configuration valid
# ✓ Data files accessible
# ✓ Parsing would create 156 components
# (No files written in dry-run mode)

# Test exporter compatibility
r2x read switch ./data | r2x write my_exporter ./output --dry-run

# Validate plugin can be loaded
r2x info my_custom_plugin

# Output:
# ✓ Plugin registered successfully
# Plugin: my_custom_plugin
# Version: 0.1.0
# Entry point: my_package.plugins:register
```

# ... benchmark performance

```bash
# Benchmark parser performance
r2x read my_plugin ./large_dataset --benchmark

# Output:
# Benchmarking my_plugin parser...
# File reading: 1.23s
# Data processing: 4.56s
# Component creation: 2.34s
# Total parsing time: 8.13s
# Components created: 15,423
# Memory usage: 234 MB
# Throughput: 1,897 components/sec

# Benchmark full translation
time r2x read switch ./data | r2x write plexos ./output

# Compare parsers
for plugin in switch reeds plexos; do
  echo "Testing $plugin..."
  time r2x read $plugin ./data/$plugin --benchmark
done
```

# ... use in automation scripts

```bash
#!/bin/bash
# batch_translate.sh - Translate multiple scenarios

SCENARIOS=("base" "high_renewables" "low_cost" "carbon_neutral")
INPUT_DIR="./scenarios"
OUTPUT_DIR="./results"
MODIFIERS="--modifier add_storage:capacity_mw=2000 --modifier emission_cap:limit_tonnes=100000"

for scenario in "${SCENARIOS[@]}"; do
  echo "Processing scenario: $scenario"

  # Read, modify, and export
  r2x read switch "${INPUT_DIR}/${scenario}" | \
    r2x run add_storage --capacity-mw 2000 | \
    r2x run emission_cap --limit-tonnes 100000 | \
    r2x write plexos "${OUTPUT_DIR}/${scenario}"

  # Check exit code
  if [ $? -eq 0 ]; then
    echo "✓ $scenario completed successfully"

    # Generate summary report
    r2x read plexos "${OUTPUT_DIR}/${scenario}" --summary > "${OUTPUT_DIR}/${scenario}/summary.txt"
  else
    echo "✗ $scenario failed"
    exit 1
  fi
done

echo "All scenarios processed successfully"
```

# ... parallel processing

```bash
#!/bin/bash
# parallel_translate.sh - Process multiple models in parallel

MODELS=("model_A" "model_B" "model_C" "model_D")

# Function to translate a single model
translate_model() {
  local model=$1
  echo "Processing $model..."

  r2x read switch "./data/$model" | \
    r2x run add_storage --capacity-mw 1500 | \
    r2x write plexos "./output/$model"

  if [ $? -eq 0 ]; then
    echo "✓ $model completed"
  else
    echo "✗ $model failed"
  fi
}

# Export function for parallel
export -f translate_model

# Run translations in parallel (max 4 concurrent)
printf '%s\n' "${MODELS[@]}" | xargs -P 4 -I {} bash -c 'translate_model "$@"' _ {}

echo "All models processed"
```

# ... data exploration and analysis

```bash
# Extract specific component types
r2x read switch ./data | \
  jq '.components[] | select(.type == "Generator")' > generators.json

# Get system statistics
r2x read reeds ./data | jq '{
  total_components: .components | length,
  component_types: [.components[].type] | unique,
  total_capacity: [.components[] | select(.type == "Generator") | .active_power] | add,
  total_demand: [.timeseries.demand[]] | add
}'

# Compare two models
diff <(r2x read switch ./data | jq -S '.components | sort_by(.name)') \
     <(r2x read plexos ./converted | jq -S '.components | sort_by(.name)')

# Export filtered subset
r2x read switch ./data | \
  jq '.components |= map(select(.type == "Generator" and .fuel_type == "solar"))' | \
  r2x write plexos ./output/solar_only

# Extract time series for analysis
r2x read switch ./data -o system.json
cat system.json | jq '.timeseries.load' | \
  python -c "import sys, json, pandas as pd; \
    data = json.load(sys.stdin); \
    df = pd.DataFrame(data); \
    print(df.describe())"
```

# ... integrate with other tools

```bash
# Use with Make for build automation
# Makefile:
.PHONY: all translate test clean

all: translate test

translate:
	r2x read switch ./data/switch | \
	  r2x run add_storage --capacity-mw 2000 | \
	  r2x write plexos ./output/plexos
	r2x read switch ./data/switch | \
	  r2x write sienna ./output/sienna

test:
	r2x read switch ./data/switch | r2x test plexos
	r2x read switch ./data/switch | r2x test sienna

clean:
	rm -rf ./output/*

# Use with Git hooks for validation
# .git/hooks/pre-commit:
#!/bin/bash
echo "Validating model files..."
r2x read switch ./data/switch --dry-run
if [ $? -ne 0 ]; then
  echo "Model validation failed!"
  exit 1
fi

# Use in CI/CD pipeline
# .github/workflows/translate.yml:
# - name: Translate models
#   run: |
#     r2x read switch ./data | r2x write plexos ./artifacts
#     r2x read switch ./data | r2x test plexos

# Use with watch for development
watch -n 5 'r2x read switch ./data --summary'
```

# ... debugging and troubleshooting

```bash
# Verbose output for debugging
r2x read switch ./data --verbose | r2x write plexos ./output --verbose

# Output:
# [DEBUG] Loading plugin: switch
# [DEBUG] Initializing DataStore with 15 files
# [DEBUG] Reading generators.csv (124 rows)
# [DEBUG] Creating 124 Generator components
# ...

# Debug with specific log level
R2X_LOG_LEVEL=DEBUG r2x read switch ./data

# Save intermediate system state for inspection
r2x read switch ./data -o debug_system.json
cat debug_system.json | jq '.components | length'

# Validate each step individually
r2x read switch ./data --dry-run
r2x run add_storage --capacity-mw 500 < system.json --dry-run
r2x write plexos ./output --dry-run < system.json

# Check for data loss in translation
r2x read switch ./data -o original.json
r2x write plexos ./temp < original.json
r2x read plexos ./temp -o roundtrip.json
diff <(jq -S . original.json) <(jq -S . roundtrip.json)
```

# ... environment configuration

```bash
# Set default plugin search paths
export R2X_PLUGIN_PATH="/usr/local/r2x/plugins:~/.r2x/plugins"

# Set default output format
export R2X_OUTPUT_FORMAT="json"

# Set log level
export R2X_LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR

# Use configuration file
r2x --config ./r2x_config.toml read switch ./data

# Configuration file (r2x_config.toml):
# [global]
# log_level = "INFO"
# plugin_paths = ["/usr/local/r2x/plugins", "~/.r2x/plugins"]
#
# [defaults.switch]
# weather_year = 2030
# include_reserves = true
#
# [defaults.plexos]
# version = "9.0"
# include_metadata = true

# List active configuration
r2x config --show

# Output:
# Active configuration:
#   Config file: ./r2x_config.toml
#   Log level: INFO
#   Plugin paths:
#     - /usr/local/r2x/plugins
#     - ~/.r2x/plugins
#   Default parameters:
#     switch.weather_year: 2030
#     plexos.version: 9.0
```
