# Regional Variant Detection

Analyze the following definition for regional usage patterns:

**Definition**: {{ definition }}

## Region Codes:
- US - United States
- UK - United Kingdom  
- AU - Australia
- CA - Canada
- IN - India
- ZA - South Africa
- IE - Ireland
- NZ - New Zealand

## Detection Guidelines:
1. Look for explicit regional markers in the definition
2. Identify region-specific terminology or spelling
3. Consider cultural or contextual clues
4. Return empty list if universally used
5. Include only regions where this specific usage is common

## Examples:
- "A lift in a building" → ["UK", "AU", "IN"] (vs. elevator in US)
- "The season between summer and winter" → ["US", "CA"] (fall vs. autumn)
- "A sweet carbonated beverage" → [] (universal, though names vary)

Identify regions where this definition's usage is common.