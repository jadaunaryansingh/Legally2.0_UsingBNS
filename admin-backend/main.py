from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from contextlib import asynccontextmanager
import firebase_admin
from firebase_admin import credentials, auth, db
# Production deployment - v1.0.1
from datetime import datetime
import os
from dotenv import load_dotenv
from typing import Optional, List
from pydantic import BaseModel
import sys
import pathlib

# Add fastapi_server to path to import its modules
sys.path.append(str(pathlib.Path(__file__).parent.parent / "fastapi_server"))

# Load environment variables
load_dotenv()

# Import BNS JSON loader for fast access to legal data
try:
    from bns_loader import get_bns_loader
    print("✓ BNS JSON loader module loaded")
except ImportError as e:
    print(f"Warning: Could not load BNS loader: {e}")
    get_bns_loader = None

# Define request/response models
class AdminLoginRequest(BaseModel):
    email: str
    password: str

class AdminLoginResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None

class UserData(BaseModel):
    id: str
    email: str
    phone: Optional[str] = None
    created_at: int  # Unix timestamp in milliseconds from Firebase
    last_login: Optional[int] = None  # Unix timestamp in milliseconds

class ChatQuery(BaseModel):
    user_id: str
    query: str
    timestamp: int  # Unix timestamp in milliseconds from Firebase
    category: Optional[str] = None

class DashboardStats(BaseModel):
    total_users: int
    total_queries: int
    active_users_today: int
    queries_today: int
    top_categories: List[dict]
    last_updated: str

class UsersListResponse(BaseModel):
    total: int
    users: List[UserData]

class QueriesListResponse(BaseModel):
    total: int
    queries: List[ChatQuery]

class LegalAdviceRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

# Initialize Firebase Admin SDK
firebase_credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
firebase_db_url = os.getenv("FIREBASE_DATABASE_URL", "")

# Try to initialize Firebase
firebase_initialized = False
try:
    if not firebase_admin._apps:
        import pathlib
        cred_path = pathlib.Path(firebase_credentials_path)
        
        # Try environment variables first (for production/Render)
        if os.getenv("FIREBASE_PRIVATE_KEY"):
            print("Loading Firebase credentials from environment variables")
            cred_dict = {
                "type": os.getenv("FIREBASE_TYPE", "service_account"),
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": os.getenv("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": os.getenv("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
                "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': firebase_db_url
            })
            firebase_initialized = True
            print("✓ Firebase Admin SDK initialized successfully from environment variables")
        elif cred_path.exists():
            # Fall back to credentials file (for local development)
            print(f"Loading Firebase credentials from file: {cred_path}")
            cred = credentials.Certificate(str(cred_path))
            firebase_admin.initialize_app(cred, {
                'databaseURL': firebase_db_url
            })
            firebase_initialized = True
            print("✓ Firebase Admin SDK initialized successfully from file")
        else:
            print(f"Firebase credentials not found. Checked env vars and file: {cred_path}")
            firebase_initialized = False
except Exception as e:
    print(f"✗ Firebase initialization error: {e}")
    firebase_initialized = False

# In-memory data storage (in production, use a real database)
admin_users = {
    os.getenv("ADMIN_EMAIL", "admin@legally.com"): os.getenv("ADMIN_PASSWORD", "Admin@123")
}

app = FastAPI(
    title="Legal AI Admin API",
    description="Admin panel API for managing legal AI assistant",
    version="1.0.0"
)

# CORS middleware
cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency for verifying admin token
async def verify_admin_token(token: str = None) -> dict:
    """Verify admin authentication token"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided"
        )
    
    # Simple token validation (in production, use proper JWT validation)
    if len(token) == 64:  # SHA256 hash length
        return {"admin": True, "token": token}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token"
    )

# Routes

@app.get("/favicon.ico")
async def favicon():
    """Serve favicon"""
    # Return a simple SVG favicon as ICO
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">⚖️</text></svg>"""
    return Response(content=svg_content, media_type="image/svg+xml")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - API information page"""
    html_path = os.path.join(os.path.dirname(__file__), "public", "index.html")
    
    # If HTML file exists, serve it
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    
    # Fallback JSON response
    return {
        "name": "Legal AI Admin API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/v1/admin/health",
            "login": "POST /api/v1/admin/login",
            "dashboard": "GET /api/v1/admin/dashboard",
            "users": "GET /api/v1/admin/users",
            "queries": "GET /api/v1/admin/queries",
            "queries_by_category": "GET /api/v1/admin/queries/category/{category}",
            "set_admin_role": "POST /api/v1/admin/set-admin-role/{user_id}",
            "delete_user": "DELETE /api/v1/admin/users/{user_id}"
        },
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.post("/api/v1/admin/login", response_model=AdminLoginResponse)
async def admin_login(credentials: AdminLoginRequest) -> AdminLoginResponse:
    """
    Admin login endpoint
    Verify admin credentials against configured admin user
    """
    stored_password = admin_users.get(credentials.email)
    
    if not stored_password or stored_password != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )
    
    try:
        # Generate a simple token (in production, use JWT or similar)
        import hashlib
        import time
        token_string = f"{credentials.email}:{time.time()}"
        simple_token = hashlib.sha256(token_string.encode()).hexdigest()
        
        return AdminLoginResponse(
            success=True,
            message="Admin login successful",
            token=simple_token
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Login failed: {str(e)}"
        )

@app.get("/api/v1/admin/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(token: str = None) -> DashboardStats:
    """Get admin dashboard statistics from Firebase"""
    await verify_admin_token(token)
    
    if not firebase_initialized:
        raise HTTPException(
            status_code=503, 
            detail="Firebase Admin SDK not initialized. Please configure Firebase service account credentials."
        )
    
    try:
        # Get Firebase Realtime Database reference
        users_ref = db.reference('users')
        chats_ref = db.reference('chats')
        
        # Fetch all users
        users_data = users_ref.get() or {}
        total_users = len(users_data)
        
        # Fetch all chats
        chats_data = chats_ref.get() or {}
        all_chats = []
        category_count = {}
        
        for user_id, user_chats in chats_data.items():
            if user_chats:
                for chat_id, chat in user_chats.items():
                    all_chats.append(chat)
                    category = chat.get('category', 'General')
                    category_count[category] = category_count.get(category, 0) + 1
        
        total_queries = len(all_chats)
        
        # Calculate today's stats
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_timestamp = int(today.timestamp() * 1000)
        
        active_users_today = sum(1 for user in users_data.values() 
                                 if user.get('lastLogin', 0) >= today_timestamp)
        queries_today = sum(1 for chat in all_chats 
                           if chat.get('timestamp', 0) >= today_timestamp)
        
        # Top categories
        top_categories = [{"category": cat, "count": count} 
                         for cat, count in sorted(category_count.items(), 
                                                 key=lambda x: x[1], reverse=True)[:5]]
        
        return DashboardStats(
            total_users=total_users,
            total_queries=total_queries,
            active_users_today=active_users_today,
            queries_today=queries_today,
            top_categories=top_categories,
            last_updated=datetime.now().isoformat()
        )
    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")

@app.get("/api/v1/admin/users", response_model=UsersListResponse)
async def get_users(
    limit: int = 50,
    offset: int = 0,
    token: str = None
) -> UsersListResponse:
    """Get list of users from Firebase"""
    await verify_admin_token(token)
    
    if not firebase_initialized:
        raise HTTPException(status_code=503, detail="Firebase not initialized")
    
    try:
        users_ref = db.reference('users')
        users_data = users_ref.get() or {}
        
        users = []
        for uid, user in users_data.items():
            created_at = user.get('createdAt', 0)
            last_login = user.get('lastLogin')
            # Ensure timestamps are integers
            if isinstance(created_at, str):
                created_at = int(created_at) if created_at else 0
            if isinstance(last_login, str):
                last_login = int(last_login) if last_login else None
            users.append(UserData(
                id=uid,
                email=user.get('email', ''),
                phone=user.get('phone'),
                created_at=created_at,
                last_login=last_login
            ))
        
        return UsersListResponse(
            total=len(users),
            users=users[offset:offset+limit]
        )
    except Exception as e:
        print(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")

@app.get("/api/v1/admin/users/{user_id}")
async def get_user_details(
    user_id: str,
    token: str = None
):
    """Get individual user details from Firebase"""
    await verify_admin_token(token)
    
    if not firebase_initialized:
        raise HTTPException(status_code=503, detail="Firebase not initialized")
    
    try:
        user_ref = db.reference(f'users/{user_id}')
        user_data = user_ref.get()
        
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        created_at = user_data.get('createdAt', 0)
        last_login = user_data.get('lastLogin')
        # Ensure timestamps are integers
        if isinstance(created_at, str):
            created_at = int(created_at) if created_at else 0
        if isinstance(last_login, str):
            last_login = int(last_login) if last_login else None
        
        return {
            "id": user_id,
            "email": user_data.get('email', ''),
            "phone": user_data.get('phone'),
            "created_at": created_at,
            "last_login": last_login,
            "display_name": user_data.get('displayName'),
            "photo_url": user_data.get('photoURL')
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching user details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user details: {str(e)}")

@app.get("/api/v1/admin/users/{user_id}/chats")
async def get_user_chats(
    user_id: str,
    limit: int = 100,
    token: str = None
):
    """Get user's chat history from Firebase"""
    await verify_admin_token(token)
    
    if not firebase_initialized:
        raise HTTPException(status_code=503, detail="Firebase not initialized")
    
    try:
        chats_ref = db.reference(f'chats/{user_id}')
        chats_data = chats_ref.get() or {}
        
        chats = []
        for chat_id, chat in chats_data.items():
            timestamp = chat.get('timestamp', 0)
            # Ensure timestamp is an integer
            if isinstance(timestamp, str):
                timestamp = int(timestamp) if timestamp else 0
            chats.append({
                "id": chat_id,
                "user_id": user_id,
                "user_email": chat.get('userEmail', ''),
                "message": chat.get('message', ''),
                "response": chat.get('response', ''),
                "category": chat.get('category', 'General'),
                "timestamp": timestamp
            })
        
        # Sort by timestamp descending
        chats.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {
            "total": len(chats),
            "chats": chats[:limit]
        }
    except Exception as e:
        print(f"Error fetching user chats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user chats: {str(e)}")

@app.get("/api/v1/admin/queries", response_model=QueriesListResponse)
async def get_user_queries(
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[str] = None,
    token: str = None
) -> QueriesListResponse:
    """Get user chat queries from Firebase"""
    await verify_admin_token(token)
    
    if not firebase_initialized:
        raise HTTPException(status_code=503, detail="Firebase not initialized")
    
    try:
        chats_ref = db.reference('chats')
        chats_data = chats_ref.get() or {}
        
        queries = []
        for uid, user_chats in chats_data.items():
            if user_id and uid != user_id:
                continue
            if user_chats:
                for chat_id, chat in user_chats.items():
                    timestamp = chat.get('timestamp', 0)
                    # Ensure timestamp is an integer
                    if isinstance(timestamp, str):
                        timestamp = int(timestamp)
                    queries.append(ChatQuery(
                        user_id=uid,
                        query=chat.get('message', ''),
                        timestamp=timestamp,
                        category=chat.get('category', 'General')
                    ))
        
        # Sort by timestamp descending
        queries.sort(key=lambda x: x.timestamp, reverse=True)
        
        return QueriesListResponse(
            total=len(queries),
            queries=queries[offset:offset+limit]
        )
    except Exception as e:
        print(f"Error fetching queries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch queries: {str(e)}")

@app.get("/api/v1/admin/queries/category/{category}", response_model=QueriesListResponse)
async def get_queries_by_category(
    category: str,
    limit: int = 50,
    offset: int = 0,
    token: str = None
) -> QueriesListResponse:
    """Get queries filtered by legal category"""
    await verify_admin_token(token)
    
    # TODO: Replace with actual filtered query data from database
    queries = [
        ChatQuery(
            user_id=f"user_{i}",
            query=f"Query about {category}: Question {i}",
            timestamp=datetime.now().isoformat(),
            category=category
        )
        for i in range(1, 11)  # Demo data
    ]
    
    return QueriesListResponse(
        total=1840,
        queries=queries[offset:offset+limit]
    )

@app.get("/api/v1/admin/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Legal AI Admin API"
    }

@app.post("/api/v1/admin/set-admin-role/{user_id}")
async def set_admin_role(
    user_id: str,
    token: str = None
):
    """Set a user as admin (admin only)"""
    await verify_admin_token(token)
    
    try:
        # Set custom claims for admin role
        auth.set_custom_user_claims(user_id, {'admin': True})
        return {
            "success": True,
            "message": f"User {user_id} set as admin"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to set admin role: {str(e)}"
        )

@app.delete("/api/v1/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    token: str = None
):
    """Delete a user completely - Auth + all data (admin only)"""
    await verify_admin_token(token)
    
    if not firebase_initialized:
        raise HTTPException(status_code=503, detail="Firebase not initialized")
    
    try:
        # Delete user from Firebase Auth
        auth.delete_user(user_id)
        
        # Delete user data from Realtime Database
        users_ref = db.reference(f'users/{user_id}')
        users_ref.delete()
        
        # Delete all user chats
        chats_ref = db.reference(f'chats/{user_id}')
        chats_ref.delete()
        
        return {
            "success": True,
            "message": f"User {user_id} and all associated data deleted successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete user: {str(e)}"
        )

class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    display_name: Optional[str] = None
    password: Optional[str] = None

@app.put("/api/v1/admin/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: UpdateUserRequest,
    token: str = None
):
    """Update user information (admin only)"""
    await verify_admin_token(token)
    
    if not firebase_initialized:
        raise HTTPException(status_code=503, detail="Firebase not initialized")
    
    try:
        print(f"Updating user {user_id} with data: {user_data}")
        
        # Update Firebase Auth user (optional fields)
        update_params = {}
        if user_data.email:
            update_params['email'] = user_data.email
        if user_data.display_name:
            update_params['display_name'] = user_data.display_name
        if user_data.password and user_data.password.strip():
            # Update password if provided
            update_params['password'] = user_data.password.strip()
        if user_data.phone and user_data.phone.strip():
            # Only update phone if it's provided and not empty
            phone = user_data.phone.strip()
            # Ensure phone is in E.164 format
            if not phone.startswith('+'):
                phone = f'+91{phone}'  # Default to India +91
            update_params['phone_number'] = phone
        
        # Try to update Firebase Auth (continue even if it fails)
        if update_params:
            try:
                auth.update_user(user_id, **update_params)
                print(f"Firebase Auth updated successfully for {user_id}")
            except Exception as auth_error:
                print(f"Firebase Auth update error (continuing anyway): {auth_error}")
                # Continue to update database
        
        # Update user data in Realtime Database
        users_ref = db.reference(f'users/{user_id}')
        db_updates = {}
        
        if user_data.email:
            db_updates['email'] = user_data.email
        if user_data.phone is not None:  # Allow empty string to clear phone
            db_updates['phone'] = user_data.phone if user_data.phone else None
        if user_data.display_name is not None:
            db_updates['displayName'] = user_data.display_name if user_data.display_name else None
        
        if db_updates:
            users_ref.update(db_updates)
            print(f"Database updated successfully for {user_id}")
        
        return {
            "success": True,
            "message": "User updated successfully",
            "user_id": user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"Update user error: {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {error_msg}"
        )

# ============ LEGAL ADVICE ENDPOINT (PUBLIC) ============

@app.post("/api/legal-advice")
async def get_legal_advice(request: LegalAdviceRequest):
    """
    Real AI endpoint for getting legal advice using Groq API
    Uses Llama 3.3 70B model for specialized legal responses with BNS PDF reference
    """
    try:
        user_message = request.message.strip()
        if not user_message:
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty"
            )
        
        print(f"Processing legal advice request: {user_message[:50]}...")
        
        # Get BNS context from JSON file (fast lookup)
        bns_context = ""
        if get_bns_loader:
            try:
                loader = get_bns_loader()
                bns_context = loader.format_for_ai(user_message)
                print(f"✓ Retrieved BNS context ({len(bns_context)} chars)")
            except Exception as e:
                print(f"Warning: Could not get BNS context: {e}")
                bns_context = ""
        
        # Use Groq API (fast, free, reliable)
        import requests
        
        groq_api_key = os.getenv('GROQ_API_KEY')
        if not groq_api_key or groq_api_key == 'your_groq_api_key_here':
            raise HTTPException(
                status_code=503,
                detail="AI service not configured. Please add GROQ_API_KEY to environment variables."
            )
        
        system_prompt = f"""You are an expert legal assistant specialized in Indian Law and International Law.

Provide accurate and educational legal information with proper citations to relevant Indian statutes.

IMPORTANT INSTRUCTIONS:
- Use the Bharatiya Nyaya Sanhita, 2023 (BNS) instead of the Indian Penal Code, 1860 (IPC).
- Do NOT reference IPC sections unless explicitly asked.
- Cite laws in this format:
  Example: Section 103, Bharatiya Nyaya Sanhita, 2023.
- Where applicable, also reference:
    - Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)
    - Bharatiya Sakshya Adhiniyam, 2023 (BSA)
    - Relevant Special Acts (e.g., IT Act, POCSO Act, etc.)

{bns_context}

Explain legal principles clearly in simple language.
Mention punishments, legal ingredients, and exceptions where applicable.
Clarify whether the offence is cognizable/non-cognizable and bailable/non-bailable when relevant.
Always recommend consulting a qualified advocate for specific legal cases."""
        
        api_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",  # Fast, high-quality model
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 1024,
            "temperature": 0.7
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"Groq API Error {response.status_code}: {response.text}")
            raise Exception(f"Groq API error: {response.status_code}")
        
        result = response.json()
        response_text = result['choices'][0]['message']['content'].strip()
        
        if not response_text:
            raise Exception("Model returned empty response")
        print(f"Generated response ({len(response_text)} chars)")
        return {"response": response_text}
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        print(f"Error in legal advice endpoint: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Provide specific error messages
        if "401" in error_msg or "unauthorized" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Invalid GROQ_API_KEY. Please verify your Groq API token."
            )
        elif "groq" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Groq API error. Please check your API key and try again."
            )
        
        raise HTTPException(
            status_code=500,
            detail=f"AI service error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("ADMIN_API_PORT", 8001))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=True
    )
