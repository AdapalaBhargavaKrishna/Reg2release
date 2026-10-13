import pymupdf
import os

DOCS_DIR = os.path.join(os.path.dirname(__file__), "sample_documents")
os.makedirs(DOCS_DIR, exist_ok=True)

# 1. Florida OIR Bulletin PDF
pdf_path_1 = os.path.join(DOCS_DIR, "FL_OIR_Bulletin_26_04M.pdf")
doc1 = pymupdf.open()
page1 = doc1.new_page(width=595, height=842) # A4

fl_text = """FLORIDA OFFICE OF INSURANCE REGULATION
INFORMATIONAL BULLETIN OIR-26-04M
DATE: October 1, 2026
TO: All Property and Casualty Insurers Authorized to Transact Homeowners Insurance in Florida
SUBJECT: Mandatory Revision of Protective Device & Mitigation Discount Factors

Pursuant to Section 627.0629, Florida Statutes, and recent administrative determinations regarding catastrophe loss mitigation, all admitted carriers writing residential property insurance are hereby notified of revisions to minimum rating discounts.

SECTION 4. PROTECTIVE AND SAFETY DEVICE RATING FACTORS
(a) Historical filings authorized a standard 5% credit (factor of 0.95) for primary structures equipped with verified storm-hardened fixtures or monitored protective systems.
(b) Effective November 1, 2026, the minimum mandatory discount for residential policies possessing certified impact-resistant openings, secondary water resistance, or approved central monitoring systems shall increase from 5% (0.95 factor) to 8% (0.92 factor).
(c) Insurers utilizing rule HO_DISC_02 or equivalent rating tables must update their rating engines prior to the effective date. All new and renewal policies bound on or after November 1, 2026, must reflect this revised factor.

Failure to adjust rating algorithms accordingly shall constitute non-compliance under Chapter 627.

Office of Insurance Regulation
Tallahassee, Florida"""

page1.insert_text((50, 60), fl_text, fontsize=10.5, fontname="helv", lineheight=1.4)
doc1.save(pdf_path_1)
doc1.close()

# 2. IRDAI Circular PDF
pdf_path_2 = os.path.join(DOCS_DIR, "IRDAI_Circular_2026_18.pdf")
doc2 = pymupdf.open()
page2 = doc2.new_page(width=595, height=842) # A4

irdai_text = """INSURANCE REGULATORY AND DEVELOPMENT AUTHORITY OF INDIA (IRDAI)
Ref: IRDAI/HLT/CIR/2026/18
Date: 15 September 2026
To: All General and Standalone Health Insurers

Subject: Modification of Guidelines on Wellness and Preventive Health Features in Retail Mediclaim Products

1. Reference is invited to Chapter V of Master Circular on Health Insurance Regulations concerning wellness credits and premium incentives.

2. Source Clause 3.2 (Wellness Incentives):
In order to promote proactive health maintenance among retail policyholders, the maximum allowable discount on renewal premium linked to annual health score assessments and teleconsultation completion is enhanced from the existing ceiling of 10% (rating multiplier 0.90) to 15% (rating multiplier 0.85).

3. All insurers maintaining product wellness rating rules (including rule IRDAI_WELL_01) are directed to file revised endorsement matrices and recalibrate automated rating calculators with effect from 1st December 2026.

Sd/-
Chief General Manager (Health)
Financial District, Nanakramguda, Hyderabad"""

page2.insert_text((50, 60), irdai_text, fontsize=10.5, fontname="helv", lineheight=1.4)
doc2.save(pdf_path_2)
doc2.close()

# Clean temporary test.pdf if present
temp_test = os.path.join(DOCS_DIR, "test.pdf")
if os.path.exists(temp_test):
    os.remove(temp_test)

print("Generated sample PDF publications successfully:")
print(f" - {pdf_path_1}")
print(f" - {pdf_path_2}")
