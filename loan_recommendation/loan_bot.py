import os
import sys
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ---------- DB CONNECTION (SUPABASE) ----------
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL", "https://ttddngnjsnmvtdqospkx.supabase.co")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR0ZGRuZ25qc25tdnRkcW9zcGt4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU3MTU1ODgsImV4cCI6MjA4MTI5MTU4OH0.Txn5x2O8natg9rgcdoSdVcVeb913B3z0ISUtMV1VYXE")

print(f"🔌 Connecting to Supabase...")
print(f"   URL: {SUPABASE_URL}")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase client created successfully!")
except Exception as e:
    print(f"❌ Failed to create Supabase client: {e}")
    sys.exit(1)

# ---------- GET ALL USERS ----------
def get_all_users():
    try:
        response = supabase.table("users").select("profile_id, name, monthly_income, credit_score").execute()
        return response.data
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []

# ---------- TEST CONNECTION ----------
def test_connection():
    try:
        response = supabase.table("loans").select("loan_id", count="exact").limit(1).execute()
        print("✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# ---------- RECOMMENDATION FUNCTION ----------
def recommend_loans(profile_id, loan_type, max_interest, interest_type='max', bank_name=None):
    try:
        print(f"\n📊 Finding loans for profile: {profile_id}")
        
        # 1. Fetch user
        print(f"   Fetching user data...")
        try:
            user_response = supabase.table("users").select("monthly_income, credit_score").eq("profile_id", profile_id).execute()
            
            if not user_response.data:
                print(f"   ⚠️  User {profile_id} not found in database")
                return []

            user = user_response.data[0]
            income = user["monthly_income"]
            credit_score = user["credit_score"]
            print(f"   ✅ Found user | Income: {income}, Credit Score: {credit_score}")
        except Exception as e:
            print(f"   ⚠️  Could not fetch user data: {e}")
            print(f"   Proceeding without user validation...")
            income = 0
            credit_score = 0

        # 2. Fetch eligible loans
        try:
            print(f"   Building query: loan_type={loan_type}, bank={bank_name}, interest {interest_type} {max_interest}%")
            
            # Start with base query
            query = supabase.table("loans").select("*")
            
            # Filter by loan type if specified
            if loan_type:
                print(f"   Adding filter: loan_type = '{loan_type}'")
                query = query.eq("loan_type", loan_type)
            
            # Filter by bank name if specified
            if bank_name:
                print(f"   Adding filter: bank_name = '{bank_name}'")
                query = query.eq("bank_name", bank_name)
            
            # Filter by interest rate
            if interest_type == 'max':
                print(f"   Adding filter: interest_rate <= {max_interest}%")
                query = query.lte("interest_rate", max_interest)
            else:  # min interest
                print(f"   Adding filter: interest_rate >= {max_interest}%")
                query = query.gte("interest_rate", max_interest)
            
            print(f"   Executing query...")
            loans_response = query.execute()
            loans = loans_response.data
            
            print(f"   ✅ Found {len(loans)} loans before user filtering")
            
            # Filter by income and credit score if user data was found
            if income > 0 and credit_score > 0:
                filtered_loans = [
                    loan for loan in loans 
                    if ((loan.get("min_income") or 0) <= income and 
                        (loan.get("min_credit_score") or 0) <= credit_score)
                ]
            else:
                filtered_loans = loans
            
            print(f"   ✅ Found {len(filtered_loans)} eligible loans after user filtering")

            # 3. Return recommendations (saving handled by app.py)
            if filtered_loans:
                print(f"   Found {len(filtered_loans)} recommendations to return")
                print(f"   ✅ Processing complete!\n")
            
            return filtered_loans
        
        except Exception as e:
            print(f"   ❌ Error fetching loans: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    except Exception as e:
        print(f"❌ Error in recommend_loans: {e}")
        import traceback
        traceback.print_exc()
        return []
