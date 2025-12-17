from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import os
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

from loan_bot import recommend_loans, get_all_users
from prompt_parser import parse_prompt

# Supabase client for saving recommendations and applications
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL", "https://ttddngnjsnmvtdqospkx.supabase.co")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Frontend URL for CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

print(f"🔌 Connecting to Supabase...")
print(f"   URL: {SUPABASE_URL}")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("✅ Supabase client created successfully!")

app = FastAPI(
    title="Loan Recommendation API",
    description="AI-powered loan recommendation system",
    version="1.0.0"
)

# CORS Configuration
if ENVIRONMENT == "production":
    # Production CORS - restrict to your frontend domain
    allowed_origins = [
        FRONTEND_URL,
        "https://your-frontend-app.onrender.com"  # Replace with actual Render frontend URL
    ]
else:
    # Development CORS
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    profile_id: str = None
    message: str

class ApplyRequest(BaseModel):
    profile_id: str
    loan_id: str | int  # Accept both string and int

class UpdateProfileRequest(BaseModel):
    class Config:
        extra = "allow"

@app.get("/")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Loan Recommendation API",
        "version": "1.0.0",
        "environment": ENVIRONMENT
    }

@app.get("/test-db")
def test_database():
    """Test database connectivity and tables"""
    try:
        print("🧪 Testing database connectivity...")
        
        # Test user_loan_reco table
        reco_test = supabase.table("user_loan_reco").select("*").limit(1).execute()
        print(f"✅ user_loan_reco table accessible: {len(reco_test.data)} rows")
        
        # Test users table
        users_test = supabase.table("users").select("profile_id").limit(3).execute()
        print(f"✅ users table accessible: {len(users_test.data)} users")
        
        # Test loans table
        loans_test = supabase.table("loans").select("loan_id").limit(3).execute()
        print(f"✅ loans table accessible: {len(loans_test.data)} loans")
        
        return {
            "status": "success",
            "tables": {
                "user_loan_reco": len(reco_test.data),
                "users": len(users_test.data),
                "loans": len(loans_test.data)
            },
            "sample_user_ids": [u.get("profile_id") for u in users_test.data],
            "supabase_url": SUPABASE_URL
        }
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        print(f"📋 Database test traceback: {traceback.format_exc()}")
        return {"status": "failed", "error": str(e)}

@app.get("/users")
def get_users():
    """Get all available users"""
    users = get_all_users()
    return {"users": users}

@app.post("/chat")
def chat(req: ChatRequest):
    print(f"\n🚀 === NEW CHAT REQUEST ===")
    print(f"📝 Message: {req.message}")
    print(f"👤 Provided profile_id: {req.profile_id}")
    
    # Use provided profile_id or get the first user
    profile_id = req.profile_id
    
    if not profile_id:
        print("🔍 No profile_id provided, searching for users...")
        users = get_all_users()
        if users:
            profile_id = users[0]['profile_id']
            print(f"✅ Using first available user: {profile_id}")
        else:
            print("❌ No users found in database")
            return {
                "reply": "❌ No users found in database. Please add a user first."
            }
    else:
        print(f"✅ Using provided profile_id: {profile_id}")

    # Test Supabase connection
    try:
        test_query = supabase.table("users").select("profile_id").eq("profile_id", profile_id).execute()
        print(f"🔗 Supabase connection test: Found {len(test_query.data)} user records for {profile_id}")
    except Exception as conn_error:
        print(f"❌ Supabase connection error: {conn_error}")

    # Check if user is actually asking for loan recommendations
    message_lower = req.message.lower()
    recommendation_keywords = [
        "recommend", "suggest", "show", "find", "loan", "need", "want", 
        "looking for", "help me", "get me", "best", "options", "which"
    ]
    
    is_loan_request = any(keyword in message_lower for keyword in recommendation_keywords)
    print(f"🤖 Is loan request: {is_loan_request} (keywords found: {[k for k in recommendation_keywords if k in message_lower]})")
    
    # Only process and save recommendations if user is actually asking for them
    if not is_loan_request:
        return {
            "reply": "👋 Hello! I'm your loan assistant. I can help you find the best loan options. Try asking me something like 'I need a personal loan' or 'Show me home loan options'."
        }
    
    parsed = parse_prompt(req.message)
    print(f"🧠 Parsed prompt: {parsed}")

    loan_type = parsed.get("loan_type")
    bank_name = parsed.get("bank_name")
    max_interest = parsed.get("max_interest") or 20  # fallback
    interest_type = parsed.get("interest_type", "max")  # 'max' or 'min'

    print(f"🔍 Search criteria:")
    print(f"   - Loan type: {loan_type}")
    print(f"   - Bank name: {bank_name}")
    print(f"   - Max interest: {max_interest}")
    print(f"   - Interest type: {interest_type}")

    query_parts = []
    if loan_type:
        query_parts.append(f"{loan_type}")
    if bank_name:
        query_parts.append(f"{bank_name}")
    if max_interest:
        query_parts.append(f"interest {interest_type} {max_interest}%")
    
    query_desc = " + ".join(query_parts) if query_parts else "ANY loans"
    print(f"🔍 Searching for {query_desc}")
    
    try:
        loans = recommend_loans(
            profile_id=profile_id,
            loan_type=loan_type,
            max_interest=max_interest,
            interest_type=interest_type,
            bank_name=bank_name
        )
        print(f"📊 recommend_loans() returned {len(loans)} loans")
    except Exception as loan_search_error:
        print(f"❌ Error in recommend_loans(): {loan_search_error}")
        import traceback
        print(f"📋 Loan search traceback: {traceback.format_exc()}")
        loans = []

    if not loans:
        criteria = []
        if loan_type:
            criteria.append(f"{loan_type}")
        if bank_name:
            criteria.append(f"from {bank_name}")
        if interest_type == 'max':
            criteria.append(f"interest rate <= {max_interest}%")
        else:
            criteria.append(f"interest rate >= {max_interest}%")
        
        msg = f"❌ No loans found matching: {' '.join(criteria)}"
        print(f"📄 Returning no loans message: {msg}")
        return {"reply": msg}

    # 💾 Save recommendations to database when user requests them
    print(f"🔍 Starting to save recommendations for user {profile_id}")
    print(f"📋 Total loans found: {len(loans)}")
    
    try:
        saved_count = 0
        all_loan_details = []  # Store all loans with timing info
        
        for i, loan in enumerate(loans, 1):
            loan_id = loan.get("loan_id")
            print(f"\n📌 Processing loan {i}/{len(loans)}: ID={loan_id}")
            
            # Check if recommendation already exists
            print(f"   🔍 Checking if recommendation already exists...")
            try:
                existing = supabase.table("user_loan_reco").select("loan_id, created_at").eq("profile_id", profile_id).eq("loan_id", loan_id).execute()
                print(f"   📊 Database query successful. Found {len(existing.data)} existing records")
            except Exception as check_error:
                print(f"   ❌ Error checking existing recommendation: {check_error}")
                existing = None
            
            if existing and existing.data:
                # Get the original recommendation time
                original_time = existing.data[0].get("created_at")
                print(f"   ⏭️ Recommendation already exists for loan {loan_id} (originally at {original_time})")
                
                # Add existing loan with timing info
                loan_with_time = loan.copy()
                loan_with_time["already_recommended"] = True
                loan_with_time["original_recommendation_time"] = original_time
                all_loan_details.append(loan_with_time)
                continue
            
            # Insert new recommendation with correct schema
            current_time = datetime.utcnow().isoformat()
            insert_data = {
                "profile_id": profile_id,
                "loan_id": loan_id,
                "created_at": current_time
            }
            
            print(f"   💾 Attempting to insert new recommendation...")
            print(f"   📝 Insert data: {insert_data}")
            
            try:
                result = supabase.table("user_loan_reco").insert(insert_data).execute()
                print(f"   📊 Insert result: {result}")
                
                if result.data and len(result.data) > 0:
                    saved_count += 1
                    print(f"   ✅ Successfully saved recommendation: User {profile_id} -> Loan {loan_id}")
                    print(f"   📋 Saved data: {result.data[0]}")
                    
                    # Add new loan with timing info
                    loan_with_time = loan.copy()
                    loan_with_time["already_recommended"] = False
                    loan_with_time["original_recommendation_time"] = current_time
                    all_loan_details.append(loan_with_time)
                else:
                    print(f"   ❌ Insert returned empty data for loan {loan_id}")
                    print(f"   🔍 Full result object: {result}")
                    # Still add to the list for response
                    loan_with_time = loan.copy()
                    loan_with_time["already_recommended"] = False
                    loan_with_time["original_recommendation_time"] = current_time
                    all_loan_details.append(loan_with_time)
                    
            except Exception as insert_error:
                print(f"   ❌ Database insert error for loan {loan_id}: {insert_error}")
                print(f"   🔍 Error type: {type(insert_error)}")
                import traceback
                print(f"   📋 Full traceback: {traceback.format_exc()}")
                
                # Still add to the list for response
                loan_with_time = loan.copy()
                loan_with_time["already_recommended"] = False
                loan_with_time["original_recommendation_time"] = current_time
                all_loan_details.append(loan_with_time)
        
        print(f"\n🎯 Final result: Saved {saved_count} new recommendations for user {profile_id}")
        recommendations_saved = saved_count > 0
        
    except Exception as e:
        print(f"⚠️ Major error in recommendation saving process: {e}")
        print(f"🔍 Error type: {type(e)}")
        import traceback
        print(f"📋 Full traceback: {traceback.format_exc()}")
        
        # Don't fail the chat, just log it
        recommendations_saved = False
        saved_count = 0
        all_loan_details = loans  # Fallback to original loans

    return {
        "reply": f"✅ Found {len(loans)} matching loan(s) for you:",
        "recommendations_saved": recommendations_saved,
        "saved_count": saved_count,
        "loans": [
            {
                "loan_id": l.get("loan_id"),
                "loan_name": f"{l.get('loan_type')} - {l.get('bank_name')}",
                "bank": l.get("bank_name"),
                "interest": l.get("interest_rate"),
                "min_amount": l.get("min_amount"),
                "max_amount": l.get("max_amount"),
                "tenure": l.get("max_tenure_months"),
                "min_income": l.get("min_income"),
                "min_credit_score": l.get("min_credit_score"),
                "already_recommended": l.get("already_recommended", False),
                "original_recommendation_time": l.get("original_recommendation_time")
            }
            for l in all_loan_details
        ]
    }

@app.get("/recommendations/{profile_id}")
def get_recommendations(profile_id: str):
    """Fetch ONLY AI-chat-recommended loans for a user with dates (from user_loan_reco)"""
    try:
        # Get loan recommendations with dates, ordered by most recent first
        reco_response = supabase.table("user_loan_reco").select("loan_id, created_at").eq("profile_id", profile_id).order("created_at", desc=True).execute()
        
        if not reco_response.data:
            return {"recommendations": []}
        
        # Group by loan_id to get the most recent recommendation date for each loan
        loan_dates = {}
        for reco in reco_response.data:
            loan_id = reco["loan_id"]
            if loan_id not in loan_dates:
                loan_dates[loan_id] = reco["created_at"]
        
        loan_ids = list(loan_dates.keys())
        
        # Fetch loan details
        loans_response = supabase.table("loans").select("*").in_("loan_id", loan_ids).execute()
        
        return {
            "recommendations": [
                {
                    "loan_id": l.get("loan_id"),
                    "loan_name": f"{l.get('loan_type')} - {l.get('bank_name')}",
                    "bank": l.get("bank_name"),
                    "interest": l.get("interest_rate"),
                    "min_amount": l.get("min_amount"),
                    "max_amount": l.get("max_amount"),
                    "tenure": l.get("max_tenure_months"),
                    "min_income": l.get("min_income"),
                    "min_credit_score": l.get("min_credit_score"),
                    "recommended_at": loan_dates.get(l.get("loan_id"))
                }
                for l in loans_response.data
            ]
        }
    except Exception as e:
        print(f"Error fetching recommendations: {e}")
        return {"recommendations": [], "error": str(e)}

@app.post("/apply")
def apply_for_loan(req: ApplyRequest):
    """Mark a loan as applied (user clicked Apply button)"""
    try:
        # Create user_applications table entry
        application = supabase.table("user_applications").insert({
            "profile_id": req.profile_id,
            "loan_id": str(req.loan_id),  # Convert to string since loan_id is TEXT in DB
            "status": "applied"
        }).execute()
        
        print(f"✅ User {req.profile_id} applied for loan {req.loan_id}")
        
        return {
            "success": True,
            "message": f"✅ Application submitted successfully!",
            "application_id": application.data[0].get("id") if application.data else None
        }
    except Exception as e:
        print(f"Error applying for loan: {e}")
        return {"success": False, "error": str(e)}

@app.get("/applied-loans/{profile_id}")
def get_applied_loans(profile_id: str):
    """Fetch all loans the user has applied for"""
    try:
        # Get applications for this user
        apps_response = supabase.table("user_applications").select("loan_id").eq("profile_id", profile_id).eq("status", "applied").execute()
        loan_ids = [a["loan_id"] for a in apps_response.data]
        
        if not loan_ids:
            return {"applied_loans": []}
        
        # Fetch loan details
        loans_response = supabase.table("loans").select("*").in_("loan_id", loan_ids).execute()
        
        return {
            "applied_loans": [
                {
                    "loan_id": l.get("loan_id"),
                    "loan_name": f"{l.get('loan_type')} - {l.get('bank_name')}",
                    "bank": l.get("bank_name"),
                    "interest": l.get("interest_rate"),
                    "min_amount": l.get("min_amount"),
                    "max_amount": l.get("max_amount"),
                    "tenure": l.get("max_tenure_months")
                }
                for l in loans_response.data
            ]
        }
    except Exception as e:
        print(f"Error fetching applied loans: {e}")
        return {"applied_loans": [], "error": str(e)}

@app.post("/update-profile")
async def update_profile(request: Request):
    """Update user profile information"""
    try:
        body = await request.json()
        print(f"📝 Update request received: {body}")
        
        profile_id = body.get("profile_id")
        if not profile_id:
            return {"success": False, "error": "profile_id required"}
        
        update_data = {"updated_at": datetime.utcnow().isoformat()}
        
        # Map frontend field names to database column names
        field_mapping = {
            "full_name": "name",  # Database column is "name"
            "phone": "phone",
            "age": "age",
            "city": "city",
            "monthly_income": "monthly_income",
            "employment_type": "employment_type",
            "years_employed": "years_employed",
            "credit_score": "credit_score",
            "existing_emi": "existing_emi",
            "pan_number": "pan_number",
            "aadhar_number": "aadhar_number"
        }
        
        for frontend_field, db_column in field_mapping.items():
            if frontend_field in body and body[frontend_field]:
                update_data[db_column] = body[frontend_field]
        
        print(f"   Updating: {update_data}")
        response = supabase.table("users").update(update_data).eq("profile_id", profile_id).execute()
        print(f"✅ Updated {profile_id}")
        return {"success": True, "message": "Profile updated!", "data": response.data[0] if response.data else None}
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.delete("/clear-recommendations/{profile_id}")
def clear_recommendations(profile_id: str):
    """Clear all recommendations for a fresh user"""
    try:
        result = supabase.table("user_loan_reco").delete().eq("profile_id", profile_id).execute()
        
        deleted_count = len(result.data) if result.data else 0
        print(f"🗑️ Cleared {deleted_count} recommendations for user {profile_id}")
        
        return {
            "success": True, 
            "message": f"Cleared {deleted_count} recommendations for fresh start.",
            "deleted_count": deleted_count
        }
    except Exception as e:
        print(f"❌ Error clearing recommendations: {e}")
        return {"success": False, "error": str(e)}

@app.post("/ensure-fresh-user/{profile_id}")
def ensure_fresh_user(profile_id: str):
    """Ensure a user starts with clean recommendations slate"""
    try:
        # Clear any existing recommendations
        result = supabase.table("user_loan_reco").delete().eq("profile_id", profile_id).execute()
        deleted_count = len(result.data) if result.data else 0
        
        print(f"🧹 Ensured fresh start for user {profile_id} - removed {deleted_count} old recommendations")
        
        return {
            "success": True,
            "message": f"User {profile_id} ready for fresh AI recommendations",
            "cleared_count": deleted_count
        }
    except Exception as e:
        print(f"❌ Error ensuring fresh user: {e}")
        return {"success": False, "error": str(e)}
