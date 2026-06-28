# Test Document Mapping

Quick reference guide for test document specifications.

## Document Details by File ID

| File ID | Type | Location | Patient Name | Date | Key Details |
|---------|------|----------|--------------|------|-------------|
| **F001** | Prescription | prescriptions/ | Rajesh Kumar | 2024-11-01 | Dr. Arun Sharma, Viral Fever |
| **F002** | Prescription | prescriptions/ | Rajesh Kumar | 2024-11-01 | Another prescription (wrong type for TC001) |
| **F003** | Prescription | prescriptions/ | Sneha Reddy | 2024-10-25 | Good quality prescription |
| **F004** | Pharmacy Bill | bills/ | N/A | N/A | **BLURRY - Unreadable (TC002)** |
| **F005** | Prescription | prescriptions/ | Rajesh Kumar | 2024-11-01 | For patient mismatch test |
| **F006** | Hospital Bill | bills/ | **Arjun Mehta** | 2024-11-01 | Wrong patient (TC003) |
| **F007** | Prescription | prescriptions/ | Rajesh Kumar | 2024-11-01 | Dr. Arun Sharma, KA/45678/2015 |
| **F008** | Hospital Bill | bills/ | Rajesh Kumar | 2024-11-01 | City Clinic, ₹1,500 |
| **F009** | Prescription | prescriptions/ | Vikram Joshi | 2024-10-15 | Dr. Sunil Mehta, Diabetes |
| **F010** | Hospital Bill | bills/ | Vikram Joshi | 2024-10-15 | ₹3,000 |
| **F011** | Hospital Bill | bills/ | Priya Singh | 2024-10-15 | Smile Dental, ₹12,000 (Root Canal + Whitening) |
| **F012** | Prescription | prescriptions/ | Suresh Patil | 2024-11-02 | Dr. Venkat Rao, MRI ordered |
| **F013** | Lab Report | reports/ | Suresh Patil | 2024-11-02 | MRI Lumbar Spine |
| **F014** | Hospital Bill | bills/ | Suresh Patil | 2024-11-02 | ₹15,000 MRI (needs pre-auth) |
| **F015** | Prescription | prescriptions/ | Amit Verma | 2024-10-20 | Dr. R. Gupta, Gastroenteritis |
| **F016** | Hospital Bill | bills/ | Amit Verma | 2024-10-20 | ₹7,500 (exceeds limit) |
| **F017** | Prescription | prescriptions/ | Ravi Menon | 2024-10-30 | Dr. S. Khan, Migraine |
| **F018** | Hospital Bill | bills/ | Ravi Menon | 2024-10-30 | ₹4,800 (4th same-day claim) |
| **F019** | Prescription | prescriptions/ | Deepak Shah | 2024-11-03 | Dr. S. Iyer, Acute Bronchitis |
| **F020** | Hospital Bill | bills/ | Deepak Shah | 2024-11-03 | Apollo Hospitals, ₹4,500 |
| **F021** | Prescription | prescriptions/ | Kavita Nair | 2024-10-28 | Vaidya T. Krishnan (Ayurveda) |
| **F022** | Hospital Bill | bills/ | Kavita Nair | 2024-10-28 | Ayur Wellness, ₹4,000 |
| **F023** | Prescription | prescriptions/ | Anita Desai | 2024-10-18 | Dr. P. Banerjee, Obesity |
| **F024** | Hospital Bill | bills/ | Anita Desai | 2024-10-18 | ₹8,000 (bariatric - excluded) |

## Test Case to Documents Mapping

| Test Case | Documents Required | Purpose |
|-----------|-------------------|---------|
| **TC001** | F001, F002 | Both prescriptions (should fail - needs bill) |
| **TC002** | F003, F004 | Good prescription + blurry bill |
| **TC003** | F005, F006 | Patient name mismatch detection |
| **TC004** | F007, F008 | Clean approval case |
| **TC005** | F009, F010 | Waiting period rejection (diabetes) |
| **TC006** | F011 | Partial approval (dental exclusion) |
| **TC007** | F012, F013, F014 | Pre-authorization missing |
| **TC008** | F015, F016 | Per-claim limit exceeded |
| **TC009** | F017, F018 | Fraud detection (same-day claims) |
| **TC010** | F019, F020 | Network hospital discount |
| **TC011** | F021, F022 | Graceful degradation test |
| **TC012** | F023, F024 | Excluded treatment (obesity) |

## Doctor Registration Numbers

| Doctor | Registration | State | Specialization |
|--------|-------------|-------|----------------|
| Dr. Arun Sharma | KA/45678/2015 | Karnataka | Internal Medicine |
| Dr. Sunil Mehta | GJ/56789/2014 | Gujarat | Endocrinology |
| Dr. Venkat Rao | AP/67890/2017 | Andhra Pradesh | Neurology |
| Dr. R. Gupta | DL/34567/2016 | Delhi | Gastroenterology |
| Dr. S. Khan | MH/78901/2019 | Maharashtra | Neurology |
| Dr. S. Iyer | TN/56789/2013 | Tamil Nadu | Pulmonology |
| Vaidya T. Krishnan | AYUR/KL/2345/2019 | Kerala | Ayurveda |
| Dr. P. Banerjee | WB/34567/2015 | West Bengal | Bariatric |

## Member ID to Name Mapping

| Member ID | Name | Policy Join Date |
|-----------|------|------------------|
| EMP001 | Rajesh Kumar | 2024-04-01 |
| EMP002 | Priya Singh | 2024-04-01 |
| EMP003 | Amit Verma | 2024-04-01 |
| EMP004 | Sneha Reddy | 2024-04-01 |
| EMP005 | Vikram Joshi | 2024-09-01 (New - waiting period applies) |
| EMP006 | Kavita Nair | 2024-04-01 |
| EMP007 | Suresh Patil | 2024-04-01 |
| EMP008 | Ravi Menon | 2024-04-01 |
| EMP009 | Anita Desai | 2024-04-01 |
| EMP010 | Deepak Shah | 2024-04-01 |

## Expected Outcomes Summary

| Test Case | Expected Decision | Expected Amount | Key Reason |
|-----------|------------------|----------------|-----------|
| TC001 | No decision | N/A | Wrong document type |
| TC002 | No decision | N/A | Unreadable document |
| TC003 | No decision | N/A | Patient name mismatch |
| TC004 | APPROVED | ₹1,350 | 10% co-pay applied |
| TC005 | REJECTED | ₹0 | Waiting period (diabetes) |
| TC006 | PARTIAL | ₹8,000 | Cosmetic exclusion |
| TC007 | REJECTED | ₹0 | Missing pre-authorization |
| TC008 | REJECTED | ₹0 | Per-claim limit exceeded |
| TC009 | MANUAL_REVIEW | N/A | Fraud signal |
| TC010 | APPROVED | ₹3,240 | Network discount + co-pay |
| TC011 | APPROVED | Variable | Component failure (graceful) |
| TC012 | REJECTED | ₹0 | Excluded condition |

---

**Note**: All dates fall within the policy period (2024-04-01 to 2025-03-31)
