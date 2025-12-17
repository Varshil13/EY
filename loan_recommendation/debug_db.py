import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Database connection
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL", "https://ttddngnjsnmvtdqospkx.supabase.co")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")

if not SUPABASE_KEY:
    print("❌ No SUPABASE_KEY found in environment")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🔍 Checking user_loan_reco table...")

try:
    # Check current contents
    result = supabase.table("user_loan_reco").select("*").execute()
    
    print(f"📊 Found {len(result.data)} total recommendations in database:")
    
    for row in result.data:
        print(f"  Profile: {row.get('profile_id')}, Loan: {row.get('loan_id')}, Date: {row.get('created_at')}")
    
    # Check specific users
    print("\n🔍 Checking for new users (U004, U005, etc)...")
    
    for user_id in ['U004', 'U005', 'U006']:
        user_recs = supabase.table("user_loan_reco").select("*").eq("profile_id", user_id).execute()
        print(f"  {user_id}: {len(user_recs.data)} recommendations")
        for rec in user_recs.data:
            print(f"    Loan: {rec.get('loan_id')}, Date: {rec.get('created_at')}")
            
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*50)
print("🧹 CLEARING ALL RECOMMENDATIONS...")

try:
    # Clear all recommendations
    result = supabase.table("user_loan_reco").delete().neq("profile_id", "NONEXISTENT").execute()
    print(f"✅ Cleared {len(result.data) if result.data else 0} recommendations")
    
    # Verify cleared
    result = supabase.table("user_loan_reco").select("*").execute()
    print(f"📊 Remaining recommendations: {len(result.data)}")
    
except Exception as e:
    print(f"❌ Error clearing: {e}")