import requests
import json

# Test the API functionality
def test_recommendations_api():
    """Test the recommendations API"""
    
    # Test user ID (make sure this exists in your database)
    user_id = "U006"
    
    try:
        # Test chat endpoint (main functionality)
        chat_url = "http://127.0.0.1:8000/chat"
        chat_data = {
            "profile_id": user_id,
            "message": "I need car loans"
        }
        
        print(f"🚀 Testing chat with: {chat_data}")
        response = requests.post(chat_url, json=chat_data)
        print(f"📊 Chat Response Status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            print(f"✅ Chat Success!")
            print(f"   Reply: {data.get('reply', 'No reply')[:100]}...")
            print(f"   Recommendations Saved: {data.get('recommendations_saved', False)}")
            print(f"   Saved Count: {data.get('saved_count', 0)}")
            
            # Test recommendations endpoint
            reco_url = f"http://127.0.0.1:8000/recommendations/{user_id}"
            print(f"\n🔄 Testing recommendations fetch...")
            reco_response = requests.get(reco_url)
            print(f"📊 Recommendations Response Status: {reco_response.status_code}")
            
            if reco_response.ok:
                reco_data = reco_response.json()
                print(f"✅ Found {len(reco_data.get('recommendations', []))} recommendations")
                for i, rec in enumerate(reco_data.get('recommendations', [])[:3]):
                    print(f"   {i+1}. {rec.get('loan_name', 'Unknown')} - {rec.get('bank', 'Unknown Bank')}")
            else:
                print(f"❌ Recommendations fetch failed: {reco_response.text}")
        else:
            print(f"❌ Chat failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Make sure the backend is running at http://127.0.0.1:8000")

if __name__ == "__main__":
    test_recommendations_api()