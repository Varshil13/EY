# Loan Recommendation Integration Setup

## Architecture Overview

The **EY website** now has an integrated AI Assistant (Chatbot) that seamlessly handles both:
1. **Loan-related queries** → Calls `loan_recommendation` backend
2. **General queries** → Calls OpenAI API

Both are displayed in the **same chat UI** on the EY website's "AI Assistant" tab.

---

## Running the System

### **Terminal 1: Start Loan Recommendation Backend**

```bash
cd d:\KodeLand\PROJECTS\loan_recommendation
python -m uvicorn app:app --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### **Terminal 2: Start EY Website Frontend**

```bash
cd d:\KodeLand\PROJECTS\EY
npm run dev
```

**Expected output:**
```
VITE v... ready in ... ms

➜  Local:   http://localhost:5173/
➜  press h to show help
```

---

## Testing the Integration

### **Step 1:** Open EY website
- Go to http://localhost:5173/
- Sign up or log in
- Navigate to **"AI Assistant"** tab on the dashboard

### **Step 2:** Test loan-related prompts
All of these should return **loan recommendations from the backend**:

- ✅ "I want a personal loan with interest less than 12%"
- ✅ "give me car loan from ICICI bank"
- ✅ "home loan with interest below 9%"
- ✅ "education loan from SBI"

### **Step 3:** Test general prompts
These will fall back to **OpenAI API**:

- ✅ "What's the capital of France?"
- ✅ "Help me understand compound interest"
- ✅ "What's the best age to buy a home?"

---

## How It Works

### **When user sends a message:**

1. **Chatbot.tsx** receives the message
2. **First attempt:** Calls `POST http://127.0.0.1:8000/chat`
   - Sends: `{ profile_id: user.profile_id, message: "user input" }`
   - If loans found → Display in chat (DONE)
   - If no loans found → Fall through to step 3
3. **Fallback:** Calls OpenAI API for a general response
4. **Display:** Response shown in same chat UI

---

## File Changes Made

### **EY\src\components\Chatbot\Chatbot.tsx**
- ✅ Now calls loan recommendation backend on every message
- ✅ Extracts user's `profile_id` from logged-in user
- ✅ Formats loan results into readable chat messages
- ✅ Falls back to OpenAI if no loans found

---

## Environment Variables

### **EY (.env.local)**
```
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
VITE_OPENAI_API_KEY=...
```

### **Loan Recommendation (.env)**
```
VITE_SUPABASE_URL=https://ttddngnjsnmvtdqospkx.supabase.co
VITE_SUPABASE_ANON_KEY=...
OPENAI_API_KEY=... (optional, for fallback)
```

---

## Database

Both projects share the same **Supabase database**:
- `users` table — User profiles (EY creates, both read)
- `loans` table — Loan products (30 loans available)
- `user_loan_reco` table — Recommendation history

---

## Troubleshooting

### **Loan backend returns "No loans found"**
- Check if loan_recommendation backend is running on `:8000`
- Verify user's `profile_id` exists in `users` table
- Check loan filtering (loan type, bank, interest rate)

### **Chatbot shows OpenAI response instead of loans**
- Loan backend might be down (check Terminal 1)
- Prompt might not contain loan keywords (check prompt parser)
- Check browser console for fetch errors

### **CORS issues**
- Loan backend has CORS enabled for all origins (`allow_origins=["*"]`)
- If issues persist, check FastAPI middleware in `app.py`

---

## Next Steps

1. **Styling:** Customize loan display format in Chatbot.tsx
2. **Apply Button:** Add "Apply Now" button to recommend loans
3. **Voice Input:** Add speech-to-text for voice queries
4. **Recommendations Tab:** Display saved recommendations from `user_loan_reco` table

---

**Status:** ✅ Integration complete and ready for testing!
