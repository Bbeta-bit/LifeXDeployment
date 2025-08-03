# Generic Rule

## Rule 1: Low Doc Eligibility by Loan Amount
**Rule ID**: Rule_1_LowDoc  
- applicable_if: loan_amount < 100000
  conditions:
    - abn_years: >=2
    - gst_required: false
    - credit_score_corporate: >=550
    - credit_score_individual: >=550
    - property_status:
      - property_backed_spousal_accepted
      - non_property_owner_accepted
    - asset_type_limits:
      - Primary: <=100000
      - Secondary: <=100000
      - MotorVehicles: <=100000
      - Tertiary: <=50000
    - max_end_of_term_years:
      - Primary: 20
      - Secondary: 10
      - Tertiary: 10
      - MotorVehicles: 10
    - credit_reference_required: false

- applicable_if: loan_amount >= 100000 AND loan_amount <= 250000
  conditions:
    - abn_years: >=2
    - gst_registration_years: >=1
    - credit_score_corporate: >=550
    - credit_score_individual: >=600
    - property_status:
      - property_backed_required: true
      - spousal_property_accepted: true
    - asset_type_limits:
      - Primary: <=250000
      - Secondary: <=250000
      - MotorVehicles: <=150000
      - Tertiary: not_applicable
    - max_end_of_term_years:
      - Primary: 20
      - Secondary: 10
      - Tertiary: not_applicable
      - MotorVehicles: 10
    - credit_reference_required: true
    - credit_reference_types:
      - asset_finance_credit_reference
      - mortgage_statements

---

## Rule 2: Full Doc Eligibility by Loan Amount
**Rule ID**: Rule_2_FullDoc  

### Full Doc Trigger Conditions
"Applicants that do not qualify for low doc can be assessed with 6 months bank statements or financials:"

- triggers:
  - credit_score: "500 - 600"
  - exceeds_max_asset_amounts: true
  - deals_over_100k_no_credit_reference: true
  - deals_over_100k_no_property_backing: true
  - boarders_and_mid_term_refinance: true
  - abn_less_than_2_years: true

### ABN Less Than 2 Years Special Conditions
- applicable_if: abn_years < 2
  special_requirements:
    - primary_assets_only: true
    - must_be_in_business: ">3 months"
    - industry_experience: "2 years"
    - deposit_requirement: "20%"
    - assessment_method: "assessed via bank statements"


## Full Doc Requirements 

### Full Doc Requirements 1
- applicable_if: loan_amount < 250000
  required_documents:
    - option_a:
      - bank_statements: "6 Months+"
    - option_b:
      - accountant_prepared_financials: "FY2024 + FY2023"
    - mandatory_for_all:
      - commitment_schedule: required

### Full Doc Requirements 2
- applicable_if: loan_amount >= 250000 AND loan_amount < 500000
  required_documents:
    - accountant_prepared_financials_only: "FY2024 + FY2023"
    - commitment_schedule: required
    - current_ato_portal_statements: required
    - good_payment_history: "Last 12 months"
    - detailed_business_background: required
    - list_of_major_clients: required

### Full Doc Requirements 3
- applicable_if: loan_amount >= 500000 AND loan_amount <= 1000000
  required_documents:
    - accountant_prepared_financials_only: "FY2024 + FY2023"
    - commitment_schedule: required
    - current_ato_portal_statements: required
    - good_payment_history: "Last 12 months"
    - detailed_business_background: required
    - list_of_major_clients: required
    - aged_debtor_and_creditor_listing: required

### Full Doc Requirements 4
- applicable_if: loan_amount > 1000000
  required_documents:
    - accountant_prepared_financials_only: "FY2024 + FY2023"  
    - commitment_schedule: required
    - current_ato_portal_statements: required
    - good_payment_history: "Last 12 months"
    - detailed_business_background: required
    - list_of_major_clients: required
    - aged_debtor_and_creditor_listing: required
    - cashflow_projections: "if available"


## Assessment Decision Flow
decision_process:
  step_1: "Determine applicant exposure amount"
  step_2: "Check if ALL Low Doc conditions are met for applicable exposure bracket"
  step_3: 
    - if_all_conditions_met: "Qualify for Low Doc assessment"
    - if_any_condition_not_met: "Does not qualify for Low Doc → Full Doc required"
  step_4: "Apply Full Doc requirements based on loan amount"
  step_5: "Apply special conditions if ABN < 2 years"

## Notes from Original Documents:
- "We accept spousal property!" appears in both Low Doc brackets
- "NOW: Max finance amount" highlighted in Low Doc guidelines
- Pink checkmarks (●) in Full Doc table indicate required documents
- "if available" notation for cashflow projections in highest bracket only


## Rule 3: Property Ownership Criteria
**Rule ID**: Rule_3_PropertyOwnership  

### If applicant is not a property owner
- min_deposit_required_percent: 20

### If property is owned by spouse
- Relationship proof required (at least one of the following):
  - Marriage certificate
  - Medicare card
  - Utility bill (water/electricity/gas)

### For asset-backed loans
- Borrower's name must appear on property title

### Proof of ownership (any one of the following accepted)
- Council rates notice (dated within past 3 months)
- Utility bill (water, electricity, or gas)



## Rule 4: Credit Reference & Additional Requirements
**Rule ID**: Rule_4_OtherConditions  

### Credit Reference Requirements

#### Asset Credit Reference
- Loan duration >= 6 months  
- Repayment ratio >= 50% of total loan amount  
- No missed payments

#### Mortgage Reference
- Loan duration >= 6 months  
- No missed payments  
- Applicant's name must be on loan (not spouse)

---

### Business Asset Purpose Requirement

- Business loan purpose **must align** with asset usage  
- If misaligned:  
  - **Accountant letter required**

---

### Settlement Process

#### Pre-settlement Conditions
- All loan conditions must be satisfied **before settlement**  
- Signed documents required via **Docusign**

#### Private Sale Requirements
- Vehicle inspection is mandatory  
- Valid vehicle registration (Rego) must be provided

---

### Fees

| Fee Type             | Amount        |
|----------------------|---------------|
| Dealer Sale Fee      | $540 (one-off)|
| Private Sale Fee     | $700 (one-off)|
| Account Fee (monthly)| $4.95         |
| Account Fee (weekly) | $1.00         |

---

### Compliance & Security Check

#### Certificate Currency
- Required if loan amount > $100,000 AUD

#### PPSR Requirements
- Asset must be PPSR clear (no encumbrances)  
- Tax invoice required before settlement

---

### Brokerage & Origination Fees

- **Brokerage Fee**: Up to 8% of loan amount (incl. GST)  
- **Origination Fee**: Up to $1,400 (incl. GST)

---

### Loan Structure

#### Terms by Product Type
- Standard: 36–60 months  
- With Primary Asset: 36–72 months  
- With Primary Motor Vehicle: 36–84 months  
- Balloon Refinance: minimum 12 months

#### Max Balloon Percentages
- 36 months → up to 40%  
- 48 months → up to 40%  
- 60 months → up to 30%

---

### Balloon Notes (Low Doc)

- Balloon refinance under **Low Doc**:  
  - **Formal inspection may not be required**  
  - Eligibility check is still mandatory

---

### PPSR Compliance (Used Vehicles)

- PPSR must be cleared before settlement  
- Certificate of Currency required if asset > $100,000 AUD  
- Valid tax invoice must include:  
  - Year  
  - VIN  
  - Usage hours

---

### ATO Portal Requirement (Full Doc)

- ATO portal link required if:  
  - Loan amount > $250,000  
  - AND application type = Full-Doc  
- Used to verify tax position before approval

---

### Application Platform

- Submit application via **MyAngle platform**  
- **Login required** to:  
  - Create deal  
  - Trigger automated eligibility checks

---

### Rule 5

#### Motor vehicles  
Passenger cars, light trucks, vans/utes, classic cars (rate loading applies) and motorbikes.  
*Note (Flexicommercial only)* – SUVs and passenger cars are **excluded** where funding equipment.

#### Primary assets  
Typical examples:  
- Heavy trucks > 4.5 t GVM  
- Light trucks < 3.5 t GVM  
- Trailers (including caravans)  
- Buses and coaches  
- Commercial motor vehicles (utes, vans, 4WDs)  
- Construction and earth-moving equipment (non-mining)  
- Excavators and other “yellow‐goods”  
- Agriculture/farming machinery  
- Materials-handling equipment, forklifts, access lifts/boom/scissor lifts  
- Prime movers (rate loading applies)

**Age limits**  
- *Resimac*: asset may be up to **25 years** old at end-of-term  
- *Flexicommercial*: asset may be up to **20 years** old at end-of-term (trailers up to **30 years**)

#### Secondary assets  
Typical examples:  
- Generators, compressors and other plant-services equipment  
- Medical / dental / laboratory devices  
- Mining plant  
- Engineering, tooling and CNC machines  
- Printing and packaging equipment  
- Forestry machinery  
- Woodworking and metal-working equipment  
- Mechanical workshop equipment  
- Tier II trucks, buses and earth-moving attachments

**Age limits**  
- *Resimac*: asset may be up to **10 years** old at end-of-term  
- *Flexicommercial*: asset may be up to **7 years** old at end-of-term

#### Tertiary assets  
Typical examples:  
- Audio-visual and security-hardware systems  
- Point-of-sale and IT hardware (including renewable-energy assets)  
- Catering and hospitality plant, portable buildings, pallet racking, fit-outs  
- Fitness equipment, conveyors, wine & beer processing, skip-bins  
- Medical lasers, testing & calibration rigs, detachable GPS units  
- Software licences eligible under Flexicommercial

**Age limits**  
- *Resimac*: asset may be up to **5 years** old at end-of-term  
- *Flexicommercial*: asset may be up to **7 years** old at end-of-term

#### Universal exclusions (apply to one or both lenders)  
Fixtures and fittings; cool rooms and spray booths; refrigeration; gym machines; hospitality equipment not otherwise listed; scaffolding, racking and temporary fencing (unless specifically allowed); food trucks; artwork; vending or gaming machines; livestock; ride-share, taxis and repairable write-offs; demountables and shipping containers; hire-car fleets; intangible assets and software (unless Flexicommercial tertiary); IT hardware (Resimac exclusion); office furniture; photocopiers/MFDs; SUVs and passenger cars (Flexicommercial equipment policy).  

---

## Rule 6: Disqualification Criteria

> Exclude immediately if any of the following matched:

- credit_score < 500  
- Financial defaults (excluding telco < $2,500)  
- Occupation:
  - Taxi drivers  
  - Uber drivers  
  - Dry hire operators  
- Asset Type: Non-accepted assets  

---

# Product Sheets

## Product: Primary01

- interest_rate: 7.99%
- max_term_years: 10

### Eligibility Criteria
- abn_years >= 2
- gst_years >= 1
- credit_score_range: 500–650
- asset_type: Primary 
- property_owner：true

### Matching Rules
- loan_amount_rules: 
  - Rule_1_LowDoc
  - Rule_2_FullDoc
- additional_rules: 
  - Rule_3_PropertyOwnership
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6




## Product: Primary02

- interest_rate: 9.75%
- max_term_years: 15

### Eligibility Criteria
- abn_years >= 2
- gst_years >= 1
- credit_score_range: 500–650
- asset_type: Primary
- property_owner：true

### Matching Rules
- loan_amount_rules:
  - Rule_1_LowDoc
  - Rule_2_FullDoc
- additional_rules:
  - Rule_3_PropertyOwnership
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6



## Product: Primary03

- interest_rate: 10.75%
- max_term_years: 20

### Eligibility Criteria
- abn_years >= 2
- gst_years >= 1
- credit_score_range: 500–650
- asset_type: Primary
- property_owner：true

### Matching Rules
- loan_amount_rules: 
  - Rule_1_LowDoc
  - Rule_2_FullDoc
- additional_rules: 
  - Rule_3_PropertyOwnership
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6



## Product: Primary04

- interest_rate: 10.05%
- max_term_years: 10

### Eligibility Criteria
- abn_years >= 2
- gst_years >= 1
- credit_score_range: 500–650
- asset_type: Primary 
- property_owner：false


### Matching Rules
- loan_amount_rules: 
  - Rule_1_LowDoc
  - Rule_2_FullDoc
- additional_rules: 
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6



## Product: Primary05

- interest_rate: 11.05%
- max_term_years: 15

### Eligibility Criteria
- abn_years >= 2
- gst_years >= 1
- credit_score_range: 500–650
- asset_type: Primary 
- property_owner：false

### Matching Rules
- loan_amount_rules: 
  - Rule_1_LowDoc
  - Rule_2_FullDoc
- additional_rules: 
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6



## Product: Primary06

- interest_rate: 16.75%
- max_term_years: 20

### Eligibility Criteria
- abn_years >= 2
- gst_years >= 1
- credit_score_range: 500–650
- asset_type: Primary 
- property_owner：false

### Matching Rules
- loan_amount_rules:
  - Rule_1_LowDoc
  - Rule_2_FullDoc
- additional_rules: 
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6



## Product: Secondary01

- interest_rate: 10.45%
- max_term_years: 10

### Eligibility Criteria
- abn_years >= 2
- gst_years >= 1
- credit_score_range: 500–650
- asset_type: Secondary 
- property_owner：true

### Matching Rules
- loan_amount_rules:
  - Rule_1_LowDoc
  - Rule_2_FullDoc
- additional_rules:
  - Rule_3_PropertyOwnership
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6



## Product: Secondary02

- interest_rate: 11.25%
- max_term_years: 10

### Eligibility Criteria
- abn_years >= 2
- gst_years >= 1
- credit_score_range: 500–650
- asset_type: Secondary 
- property_owner：false


### Matching Rules
- loan_amount_rules:
  - Rule_1_LowDoc
  - Rule_2_FullDoc
- additional_rules: 
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6



## Product: Tertiary01

- interest_rate: 12.95%
- max_term_years: 10

### Eligibility Criteria
- abn_years >= 2
- gst_years >= 1
- credit_score_range: 500–650
- asset_type: Tertiary 
- property_owner：true

### Matching Rules
- loan_amount_rules: 
  - Rule_1_LowDoc
  - Rule_2_FullDoc
- additional_rules: 
  - Rule_3_PropertyOwnership
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6



## Product: Tertiary02

- interest_rate: 16.95%
- max_term_years: 10

### Eligibility Criteria
- abn_years >= 2
- gst_years >= 1
- credit_score_range: 500–650
- asset_type: Tertiary 
- property_owner：false

### Matching Rules
- loan_amount_rules: 
  - Rule_1_LowDoc
  - Rule_2_FullDoc
- additional_rules: 
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6




## Product: Startup01

- interest_rate: 12.95%

### Eligibility Criteria
- abn_years < 2
- gst_years == N/A
- credit_score_range >= 500
- asset_type: Start-up 
- property_owner：true

### Matching Rules
- loan_amount_rules: 
  - Rule_2_FullDoc
- additional_rules: 
  - Rule_3_PropertyOwnership
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6



## Product: Startup02

- interest_rate: 16.95%

### Eligibility Criteria
- abn_years < 2
- gst_years == N/A
- credit_score_range >= 500
- asset_type: Start-up 
- property_owner：false

### Matching Rules
- loan_amount_rules: 
  - Rule_2_FullDoc
- additional_rules
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6




## Product: GST_Exempt_PropertyOwner

- interest_rate: 11.95%

### Eligibility Criteria
- abn_years >= 2
- gst_years < 1
- gst_registered: false
- credit_score_range >= 550
- property_owner：true

### Matching Rules

- loan_amount_rules:
  - if: loan_amount <= 100000
    doc_type: LowDoc
    conditions:
      - abn_years >= 2
      - gst_required: false
      - credit_score_corporate >= 550
      - credit_score_individual >= 550
      - property_status: Property backed (Spousal accepted)
      - max_cost: 100000
      - credit_references_required: false
      - max_term_years: 10–20

  - if: loan_amount >= 250000
    doc_type: FullDoc
    use_rule: Rule_2_FullDoc
- additional_rules: 
  - Rule_3_PropertyOwnership
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6


## Product: StartUp_NonPropertyOwner

- interest_rate: 16.95%

### Eligibility Criteria
- abn_years < 2
- gst_registered: false
- credit_score_range >= 500
- property_owner：false

### Matching Rules
- loan_amount_rules:
  - Rule_2_FullDoc
- additional_rules:
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6




## Product: GST_Exempt_NonPropertyOwner

- interest_rate: 11.95%

### Eligibility Criteria
- abn_years >= 2
- gst_years < 1
- gst_registered: false
- credit_score_range >= 550
- property_owner：false

### Matching Rules

- loan_amount_rules:
  - if: loan_amount <= 100000
    doc_type: LowDoc
    conditions:
      - abn_years >= 2
      - gst_required: false
      - credit_score_corporate >= 550
      - credit_score_individual >= 550
      - property_status: Property backed (Spousal accepted)
      - max_cost: 100000
      - credit_references_required: false
      - max_term_years: 10–20
  - if: loan_amount >= 250000
    doc_type: FullDoc
    use_rule: Rule_2_FullDoc

- additional_rules:
  - Rule_3_PropertyOwnership
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6



## Product: Standard A+ Rate

**Interest Rate**: 6.99%  

### Eligibility Rules

- abn_years >= 4
- gst_years >= 2
- asset_type: Primary & Secondary  
- End of Term: Up to 10 years EOT  
  - For Secondary assets: Year of Manufacture (YOM) must be < 5 years  
- Applicant type: Must be **Company**, **Trust**, or **Partnership** (Sole Traders not accepted)  
- Credit Score Requirements:
  - Corporate >= 550
  - Individual >= 600
- Property backed: Required  

### Additional Considerations
- Business continuity: Accepted  
- Private sale loading: Not allowed  
- Minimum deal size: No minimum requirement  

### Matching Rules
- Rule_3_PropertyOwnership
- Rule_4_OtherConditions
- Rule 5
- RUle 6


## Product: A+ Rate with Discount

**Interest Rate**: 6.49%

### Eligibility Rules
- ABN registration >= 4 years  
- GST registration >= 2 years  
- Asset type allowed: Primary & Secondary  
- End of Term: Up to 10 years EOT  
  - For Secondary assets: Year of Manufacture (YOM) must be < 5 years  
- Applicant type: Must be **Company**, **Trust**, or **Partnership** (Sole Traders not accepted)  
- Credit Score Requirements:
  - Corporate >= 550
  - Individual >= 600
- Property backed: Required  
- Minimum Deal Size: >= $300,000  

### Additional Considerations   
- Business continuity: Accepted  
- Private sale loading: Not allowed  
  
### Matching Rules
- Rule_3_PropertyOwnership
- Rule_4_OtherConditions
- Rule 5
- RUle 6



## Product: A+ Rate (New Assets Only)

**Interest Rate**: 6.99%

### Eligibility Rules
- ABN registration >= 8 years  
- GST registration >= 4 years  
- Asset type allowed: Primary only  
- End of Term: Only for **New Assets** (Year of Manufacture >= 2022)  
- Applicant type: Must be **Company**, **Trust**, or **Partnership** (Sole Traders not accepted)   
- Credit Score Requirements:
  - Corporate >= 550
  - Individual >= 600
- Property backed: Required  
- Minimum Deal Size: No minimum  

### Additional Considerations
- Business continuity: Not accepted  
- Private sale loading: Not allowed  

### Matching Rules
- loan_amount_rules: 
  - Rule_2_FullDoc  
- additional_rules: 
  - Rule_3_PropertyOwnership
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6



## Product: A+ Rate with Discount (New Assets)

**Interest Rate**: 5.99%

- abn_years >= 8
- gst_years >= 4
- asset_type == Primary
- yom >= 2022  # Year of Manufacture
- Applicant type: Must be **Company**, **Trust**, or **Partnership** (Sole Traders not accepted)  
- credit_score_corporate >= 550
- credit_score_individual >= 600
- property_backed == true
- loan_amount >= 300000

### Additional Conditions
- Business continuity: Not accepted  
- Private sale loading: Not allowed  

### Matching Rules
- loan_amount_rules: 
  - Rule_2_FullDoc
- additional_rules: 
  - Rule_3_PropertyOwnership,
  - Rule_4_OtherConditions
  - Rule 5
  - RUle 6