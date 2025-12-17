from openai import OpenAI
from dotenv import load_dotenv
import json
import os
import re

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

def parse_prompt_local(user_prompt):
    """Simple local parser for common loan queries - no API needed"""
    
    loan_types = {
        "home": "Home Loan",
        "house": "Home Loan",
        "property": "Home Loan",
        "personal": "Personal Loan",
        "education": "Education Loan",
        "student": "Education Loan",
        "car": "Car Loan",
        "vehicle": "Car Loan",
        "auto": "Car Loan",
        "business": "Business Loan",
        "gold": "Gold Loan"
    }
    
    banks = {
        "hdfc": "HDFC Bank",
        "icici": "ICICI Bank",
        "sbi": "SBI",
        "axis": "Axis Bank",
        "kotak": "Kotak Mahindra",
        "bajaj": "Bajaj Finserv",
        "muthoot": "Muthoot Finance",
        "manappuram": "Manappuram Finance",
        "tata": "Tata Motors Finance",
        "mahindra": "Mahindra Finance",
        "avanse": "Avanse Financial",
        "federal": "Federal Bank",
        "lic": "LIC Housing",
        "credila": "HDFC Credila"
    }
    
    prompt_lower = user_prompt.lower()
    loan_type = None
    bank_name = None
    max_interest = None
    
    # Extract loan type
    for keyword, loan in loan_types.items():
        if keyword in prompt_lower:
            loan_type = loan
            break
    
    # Extract bank name
    for keyword, bank in banks.items():
        if keyword in prompt_lower:
            bank_name = bank
            break
    
    # Extract interest rate using regex
    # Handle both "less than" and "more than" patterns
    interest_patterns = [
        # "interest less than 12%" or "interest below 13%"
        (r'interest\s+(?:less than|below|<)\s*(\d+(?:\.\d+)?)', 'max'),
        # "interest more than 12%" or "interest above 13%"
        (r'interest\s+(?:more than|above|>)\s*(\d+(?:\.\d+)?)', 'min'),
        # "interest 12%" or "12% interest"
        (r'interest\s+(?:rate\s+)?(?:of\s+)?(\d+(?:\.\d+)?)', 'max'),
        (r'(\d+(?:\.\d+)?)\s*%\s*(?:interest|or less|or below)', 'max'),
    ]
    
    interest_type = 'max'  # Default to max_interest
    for pattern, itype in interest_patterns:
        match = re.search(pattern, prompt_lower)
        if match:
            max_interest = float(match.group(1))
            interest_type = itype
            break
    
    return {
        "loan_type": loan_type,
        "bank_name": bank_name,
        "max_interest": max_interest,
        "interest_type": interest_type  # 'max' or 'min'
    }

def parse_prompt(user_prompt):
    """Parse loan requirement from user prompt"""
    
    # Try local parser first (no API call needed)
    result = parse_prompt_local(user_prompt)
    
    # If both extracted, return immediately
    if result["loan_type"] and result["max_interest"]:
        print(f"✅ Parsed locally: {result}")
        return result
    
    # If API key available and local parser didn't get good results, try OpenAI
    if api_key and (not result["loan_type"] or not result["max_interest"]):
        try:
            print(f"🤖 Using OpenAI for parsing: {user_prompt}")
            client = OpenAI(api_key=api_key)
            
            system_prompt = """
Extract loan requirements from the user message.
Return ONLY valid JSON with no extra text.

Format:
{
  "loan_type": "one of: Home Loan, Personal Loan, Education Loan, Car Loan, Business Loan, Gold Loan, or null",
  "max_interest": number or null
}

Rules:
- If loan type is not mentioned, return null
- If interest rate is not mentioned, return null for max_interest
- Extract the max interest rate mentioned by the user
"""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0
            )
            
            try:
                openai_result = json.loads(response.choices[0].message.content)
                # Merge with local parser results, preferring non-null values
                if openai_result.get("loan_type"):
                    result["loan_type"] = openai_result["loan_type"]
                if openai_result.get("max_interest"):
                    result["max_interest"] = openai_result["max_interest"]
                    
            except json.JSONDecodeError as e:
                print(f"⚠️  Failed to parse OpenAI response: {response.choices[0].message.content}")
                
        except Exception as e:
            print(f"⚠️  OpenAI API error (using local parser): {e}")
    
    # Provide fallback default
    if not result["max_interest"]:
        result["max_interest"] = 20  # Default max interest
    
    print(f"✅ Final parsed result: {result}")
    return result
