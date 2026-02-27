import { useState, useRef, useEffect } from "react";
import Layout from "@/components/Layout";
import { Send, Scale, BookOpen, AlertCircle } from "lucide-react";
import BalanceScaleLoader from "@/components/BalanceScaleLoader";
import { auth, onAuthStateChangedWithAuth, saveChatMessage, getUserChats, saveUserData } from "@/services/firebase";

interface Message {
  id: string;
  type: "user" | "ai";
  content: string;
  loading?: boolean;
  timestamp?: Date;
}

// Use FastAPI backend endpoint - always use VITE_API_BASE_URL
const BASE_API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const LEGAL_API_URL = `${BASE_API_URL}/api/legal-advice`;

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      type: "ai",
      content:
        "Welcome to Legally. I'm your intelligent legal assistant, specialized in Indian law and regulations. Ask me about any legal matter—crimes, contracts, civil disputes, or specific acts. I'll provide comprehensive guidance based on applicable laws.",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [chatHistoryLoaded, setChatHistoryLoaded] = useState(false);
  const [authUserId, setAuthUserId] = useState<string | null>(null);
  const [authUserEmail, setAuthUserEmail] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const unsubscribe = onAuthStateChangedWithAuth((user) => {
      if (user) {
        setAuthUserId(user.uid);
        setAuthUserEmail(user.email || null);
        localStorage.setItem("userId", user.uid);
        localStorage.setItem("userEmail", user.email || "");
      } else {
        setAuthUserId(null);
        setAuthUserEmail(null);
      }
    });

    return () => unsubscribe();
  }, []);

  const ensureUserSession = async () => {
    const firebaseUser = auth.currentUser;
    const userId = firebaseUser?.uid || authUserId;
    const userEmail = firebaseUser?.email || authUserEmail || localStorage.getItem("userEmail");

    if (!userId) {
      throw new Error("No authenticated user session available");
    }

    const resolvedEmail = userEmail || `anon-${userId}@legally.app`;

    localStorage.setItem("userId", userId);
    localStorage.setItem("userEmail", resolvedEmail);

    await saveUserData({
      uid: userId,
      email: resolvedEmail,
    });

    return { userId, userEmail: resolvedEmail };
  };

  // Initialize anonymous user if not logged in
  // Load chat history from Firebase on mount
  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        if (chatHistoryLoaded) return;
        if (!authUserId) return;

        const { userId } = await ensureUserSession();
        if (!userId) return;

        const chatHistory = await getUserChats(userId);
        
        if (chatHistory.length > 0) {
          // Convert Firebase chat history to Message format
          const historicalMessages: Message[] = chatHistory.flatMap((chat) => [
            {
              id: `${chat.id}-user`,
              type: "user" as const,
              content: chat.message,
              timestamp: new Date(chat.timestamp),
            },
            {
              id: `${chat.id}-ai`,
              type: "ai" as const,
              content: chat.response,
              timestamp: new Date(chat.timestamp),
            },
          ]);

          // Prepend greeting message and append historical messages
          setMessages((prev) => [...prev, ...historicalMessages]);
        }
        
        setChatHistoryLoaded(true);
      } catch (error) {
        console.error("Error loading chat history:", error);
      }
    };

    loadChatHistory();
  }, [authUserId, chatHistoryLoaded]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputValue.trim()) return;

    try {
      await ensureUserSession();
    } catch (error) {
      console.error("Unable to create chat session:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          type: "ai",
          content: "Unable to start a chat session. Please sign in again and retry.",
        },
      ]);
      return;
    }

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: inputValue,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    // Add loading AI message
    const loadingMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: "ai",
      content: "",
      loading: true,
    };

    setMessages((prev) => [...prev, loadingMessage]);

    // Call the FastAPI backend – and fall back to a local mock response on error
    try {
      const res = await fetch(LEGAL_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: inputValue }),
      });

      if (!res.ok) {
        throw new Error("Failed to get response");
      }

      const data = await res.json();

      const aiResponse: Message = {
        id: (Date.now() + 2).toString(),
        type: "ai",
        content: data.response || "Sorry, I couldn't process that.",
      };

      setMessages((prev) => {
        // Remove loading message and add response
        return [...prev.slice(0, -1), aiResponse];
      });

      // Save chat message to Firebase
      try {
        const { userId, userEmail } = await ensureUserSession();
        await saveChatMessage({
          userId,
          userEmail,
          message: inputValue,
          response: aiResponse.content,
          category: data.category || "General",
        });
      } catch (saveError) {
        console.error("Error saving chat to Firebase:", saveError);
      }
    } catch (error) {
      console.error("Error fetching legal advice, using mock response instead:", error);

      // Fallback: use local mock response so the user still gets an answer
      const mockContent = generateMockResponse(inputValue);
      const fallbackResponse: Message = {
        id: (Date.now() + 2).toString(),
        type: "ai",
        content: mockContent,
      };

      setMessages((prev) => [...prev.slice(0, -1), fallbackResponse]);

      // Save fallback chat message to Firebase
      try {
        const { userId, userEmail } = await ensureUserSession();
        await saveChatMessage({
          userId,
          userEmail,
          message: inputValue,
          response: fallbackResponse.content,
          category: "General",
        });
      } catch (saveError) {
        console.error("Error saving fallback chat to Firebase:", saveError);
      }
    }

    setIsLoading(false);
  };

  const generateMockResponse = (query: string): string => {
    // Original mock response generator, now wrapped to reference the user's query
    const responses: { [key: string]: string } = {
      theft: `**Indian Penal Code - Theft**

**Definition:** Theft is defined under Section 378 of the IPC as moving any property with the intention of causing wrongful loss to any person.

**Applicable Sections:**
• **Section 378 IPC** - Definition of theft
• **Section 379 IPC** - Punishment for theft (up to 3 years imprisonment)
• **Section 380 IPC** - Theft in dwelling house or place of worship

**Key Points:**
- The perpetrator must have the intent to cause wrongful loss
- The property must be moved with this intention
- It is a cognizable offense
- Punishment ranges from 3 months to 3 years imprisonment

**Note:** This is educational information only. Consult a lawyer for case-specific advice.`,
      accident: `**Motor Vehicles Act - Road Accident**

**Applicable Sections:**
• **Section 133 MV Act** - Power to impound vehicles
• **Section 134 MV Act** - Duty of driver in case of accident
• **Section 161 MV Act** - Compensation by insurer

**Key Obligations:**
1. Stop immediately and provide assistance
2. Report to nearest police station
3. Exchange information with other parties
4. File insurance claim if applicable

**Compensation:**
- Death: up to ₹1,00,000
- Permanent disability: up to ₹50,000
- Temporary injury: up to ₹25,000

**Note:** Insurance verification is mandatory. Consult a lawyer for accident claims.`,
      default: `**Legal Inquiry Response**

I can help you understand Indian laws across various areas including:

**Criminal Law:**
- Indian Penal Code (IPC)
- Criminal Procedure Code (CrPC)
- Specific Act violations

**Civil Law:**
- Contract disputes
- Property issues
- Family law matters

**Special Laws:**
- Consumer Protection Act
- Labor Law
- Environmental Protection Act

**To get specific information:**
1. Describe the situation clearly
2. Mention relevant parties involved
3. Specify the location (for jurisdiction)

Please provide more details about your query so I can provide accurate legal information.`,
    };

    const lowerQuery = query.toLowerCase();
    const questionLine =
      query.trim().length > 0
        ? `You asked about:\n\n> **${query.trim()}**\n\n`
        : "";

    // Special handling for homicide / murder style queries
    if (
      lowerQuery.includes("murder") ||
      lowerQuery.includes("killed") ||
      lowerQuery.includes("kill") ||
      lowerQuery.includes("homicide")
    ) {
      const murderResponse = `**Indian Penal Code – Homicide / Murder (Educational Overview)**

**Key Concepts:**
• **Section 299 IPC** – Culpable homicide (causing death with the intention of causing death, or with the intention/knowledge that the act is likely to cause death).  
• **Section 300 IPC** – Murder (a more serious form of culpable homicide where specific aggravated conditions are satisfied).  
• **Sections 302–304 IPC** – Punishment provisions for murder and culpable homicide.

**Typical Legal Consequences (if guilt is proved):**
• **Section 302 IPC (Murder):** Death penalty or imprisonment for life, and fine.  
• **Section 304 IPC (Culpable homicide not amounting to murder):** Imprisonment which may extend to life or up to 10 years, plus fine, depending on the facts and intention.

**Criminal Procedure (CrPC) Aspects:**
• Such offences are **cognizable**, **non-bailable**, and triable by a **Court of Session**.  
• Police can register an FIR, investigate, arrest, and file a charge sheet before the competent court.  

**Very Important Disclaimer:**
- This information is a **general explanation of Indian law** only.  
- If there is any real incident, the person concerned should **immediately consult a criminal lawyer** and cooperate with due process of law.  
- This AI does **not** encourage or assist in any unlawful activity; it only explains what the law says.`;

      return questionLine + murderResponse;
    }

    for (const [key, response] of Object.entries(responses)) {
      if (lowerQuery.includes(key)) {
        return questionLine + response;
      }
    }

    return questionLine + responses.default;
  };

  return (
    <Layout>
      <div className="max-w-5xl mx-auto h-[calc(100vh-180px)] flex flex-col">
        {/* Header */}
        <div className="border-b border-white/10 px-6 py-6 animate-fade-in">
          <div className="flex items-center gap-3 mb-2">
            <Scale className="w-6 h-6 text-white/80" />
            <h1 className="text-3xl font-bold text-white animate-dancing-glow">
              Legally Assistant
            </h1>
          </div>
          <p className="text-white/60 text-sm">
            Expert analysis of Indian laws, regulations, and legal procedures
          </p>
        </div>

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto px-6 py-8 space-y-8">
          {messages.map((message, index) => (
            <div
              key={message.id}
              className={`flex ${
                message.type === "user" ? "justify-end" : "justify-start"
              } animate-slide-up`}
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              {message.type === "ai" && (
                <div className="mr-4 flex-shrink-0">
                  <div className="w-10 h-10 rounded-full bg-white/10 border border-white/20 flex items-center justify-center">
                    <BookOpen className="w-5 h-5 text-white/60" />
                  </div>
                </div>
              )}

              <div
                className={`max-w-2xl ${
                  message.type === "user" ? "rounded-2xl" : "rounded-2xl"
                } ${
                  message.type === "user"
                    ? "bg-gradient-to-br from-white to-white/90 text-black shadow-lg shadow-white/20"
                    : "bg-white/5 text-white border border-white/10 hover:border-white/20 hover:bg-white/10 transition-all duration-300"
                } p-6 ${
                  message.type === "user"
                    ? "transform hover:shadow-xl hover:shadow-white/30 active:scale-95"
                    : ""
                }`}
              >
                {message.loading ? (
                  <div className="flex flex-col items-center justify-center gap-4 py-12">
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-white/60 animate-pulse"></div>
                      <div className="w-2 h-2 rounded-full bg-white/60 animate-pulse" style={{ animationDelay: "0.2s" }}></div>
                      <div className="w-2 h-2 rounded-full bg-white/60 animate-pulse" style={{ animationDelay: "0.4s" }}></div>
                    </div>
                    <p className="text-white/50 text-sm">Analyzing legal information...</p>
                  </div>
                ) : (
                  <div className="whitespace-pre-wrap text-sm md:text-base leading-relaxed">
                    {message.content.split("\n").map((line, idx) => {
                      // Bold headers
                      if (line.startsWith("**") && line.endsWith("**")) {
                        return (
                          <div
                            key={idx}
                            className="font-bold mt-5 mb-3 text-lg first:mt-0 animate-glow-text"
                          >
                            {line.replace(/\*\*/g, "")}
                          </div>
                        );
                      }
                      // Bold inline text
                      if (line.includes("**")) {
                        return (
                          <div key={idx}>
                            {line.split("**").map((part, i) =>
                              i % 2 === 1 ? (
                                <span key={i} className="font-bold text-white">
                                  {part}
                                </span>
                              ) : (
                                <span key={i}>{part}</span>
                              )
                            )}
                          </div>
                        );
                      }
                      // Bullet points
                      if (line.startsWith("•")) {
                        return (
                          <div key={idx} className="ml-6 my-1 flex gap-3">
                            <span className="flex-shrink-0">•</span>
                            <span>{line.substring(1)}</span>
                          </div>
                        );
                      }
                      return (
                        <div key={idx} className={line === "" ? "h-3" : "my-1"}>
                          {line}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {message.type === "user" && (
                <div className="ml-4 flex-shrink-0 text-xs text-white/40">
                  {message.timestamp &&
                    message.timestamp.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Box */}
        <div className="border-t border-white/10 px-6 py-6 bg-black/50 backdrop-blur-sm">
          <form onSubmit={handleSendMessage} className="flex gap-4">
            <div className="flex-1 flex gap-2">
              <button
                type="button"
                className="flex-shrink-0 p-3 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 hover:border-white/20 transition-all duration-300 text-white/60 hover:text-white/80 group"
                title="Quick suggestions"
              >
                <AlertCircle className="w-5 h-5 transform group-hover:scale-110 transition-transform" />
              </button>
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask about a law, crime scenario, legal act, or regulation…"
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-6 py-4 text-white placeholder-white/40 focus:outline-none focus:border-white/30 focus:ring-2 focus:ring-white/20 transition-all duration-300 focus:bg-white/10 hover:border-white/20"
                disabled={isLoading}
              />
            </div>
            <button
              type="submit"
              disabled={isLoading || !inputValue.trim()}
              className="group relative bg-white text-black px-8 py-4 rounded-lg font-semibold hover:bg-white/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 active:scale-95 transform hover:scale-105 hover:shadow-lg hover:shadow-white/40 overflow-hidden flex-shrink-0"
            >
              <span className="absolute inset-0 bg-black/20 transform scale-0 group-active:scale-100 transition-transform duration-500 origin-center rounded-lg"></span>
              <span className="relative z-10 flex items-center gap-2">
                {isLoading ? (
                  <div className="flex gap-1">
                    <div className="w-2 h-2 rounded-full bg-black animate-pulse"></div>
                    <div
                      className="w-2 h-2 rounded-full bg-black animate-pulse"
                      style={{ animationDelay: "0.2s" }}
                    ></div>
                    <div
                      className="w-2 h-2 rounded-full bg-black animate-pulse"
                      style={{ animationDelay: "0.4s" }}
                    ></div>
                  </div>
                ) : (
                  <>
                    <Send className="w-5 h-5 transform group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
                    <span className="hidden sm:inline">Send</span>
                  </>
                )}
              </span>
            </button>
          </form>

          {/* Info Note */}
          <p className="text-xs text-white/40 mt-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            This AI provides legal information for educational purposes only. Always consult a qualified legal professional.
          </p>
        </div>
      </div>
    </Layout>
  );
}
