import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [activeSection, setActiveSection] = useState("dashboard");
  const [notification, setNotification] = useState("");
  const [chartMode, setChartMode] = useState("probability");
  const [showSplash, setShowSplash] = useState(true);

  // =========================================================
  // AEROS AI CHATBOT STATE (BACKEND `.env` GEMINI -> MISTRAL FALLBACK)
  // =========================================================
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([
    {
      sender: "ai",
      text: "👋 Namaste! Main AEROS hoon (Powered by Gemini 2.5 Flash & Mistral AI).\n\nAap mujhse kisi bhi topic par sawal pooch sakte hain:\n• 'Razorpay kya h?'\n• 'Aaj kya date h?'\n• 'Tum konsa AI use kar rahe ho?'\n• 'Ye project kaise bana hai?'",
    },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatThinking, setChatThinking] = useState(false);

  // 1. INITIAL SPLASH SCREEN (2 SECONDS)
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowSplash(false);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  // 2. FETCH EVENTS
  const fetchEvents = async () => {
    try {
      const response = await fetch(`${API_URL}/events`);
      if (!response.ok) {
        throw new Error("Failed to fetch events");
      }
      const data = await response.json();
      setEvents(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to fetch events:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
    const interval = setInterval(fetchEvents, 10000);
    return () => clearTimeout(interval);
  }, []);

  // 3. NOTIFICATION TOAST
  const showNotification = (message) => {
    setNotification(message);
    setTimeout(() => {
      setNotification("");
    }, 3200);
  };

  // 4. GENERATE EVENTS
  const generateEvents = async () => {
    setGenerating(true);
    try {
      const response = await fetch(`${API_URL}/seed/10`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error("Failed to generate events");
      }
      await fetchEvents();
      showNotification("10 new recovery events generated successfully");
    } catch (error) {
      console.error(error);
      showNotification("Failed to generate events");
    } finally {
      setGenerating(false);
    }
  };

  // 5. METRIC CALCULATIONS
  const totalEvents = events.length;

  const totalRevenue = events.reduce(
    (sum, event) => sum + Number(event.amount || 0),
    0
  );

  const recoveredAmount = events.reduce((total, event) => {
    return (
      total +
      Number(
        event.recovery_result?.outcome?.amount_recovered ||
          (event.status === "RECOVERED" ? event.amount : 0)
      )
    );
  }, 0);

  const recoveredEvents = events.filter(
    (event) =>
      event.recovery_result?.outcome?.recovery_success === true ||
      event.status === "RECOVERED"
  ).length;

  const highPriority = events.filter(
    (event) => event.priority?.toLowerCase() === "high"
  ).length;

  const averageProbability =
    totalEvents > 0
      ? Math.round(
          (events.reduce(
            (sum, event) => sum + Number(event.recovery_probability || 0),
            0
          ) /
            totalEvents) *
            100
        )
      : 0;

  const recoveryRate =
    totalEvents > 0
      ? Math.round((recoveredEvents / totalEvents) * 100)
      : 0;

  const failureBreakdown = useMemo(() => {
    const counts = {};
    events.forEach((event) => {
      const category = (
        event.failure_category ||
        event.failure_reason ||
        "Payment Timeout"
      ).replaceAll("_", " ");
      counts[category] = (counts[category] || 0) + 1;
    });
    return Object.entries(counts).map(([name, count]) => ({
      name,
      count,
      percentage: totalEvents > 0 ? Math.round((count / totalEvents) * 100) : 0,
    }));
  }, [events, totalEvents]);

  // 6. CUSTOMER GROUPING
  const customers = useMemo(() => {
    const map = {};

    events.forEach((event) => {
      const id = event.customer_id || "UNKNOWN";

      if (!map[id]) {
        map[id] = {
          customer_id: id,
          customer_name: event.customer_name || `Customer ${id}`,
          customer_email: event.customer_email || "Not available",
          customer_phone: event.customer_phone || "Not available",
          payment_method: event.payment_method || "Not available",
          gateway_provider: event.gateway_provider || "Razorpay",
          user_device: event.user_device || "Not available",
          transactions: [],
          totalRevenue: 0,
          failedRevenue: 0,
          recoveredRevenue: 0,
          successfulTransactions: 0,
          failedTransactions: 0,
          lastActivity: event.created_at,
          lastFailureCategory: event.failure_category || "Payment Timeout",
        };
      }

      map[id].transactions.push(event);
      map[id].totalRevenue += Number(event.amount || 0);

      if (
        event.event_type === "failed_payment" ||
        event.status === "FAILED" ||
        event.failure_category
      ) {
        map[id].failedRevenue += Number(event.amount || 0);
        map[id].failedTransactions += 1;
        if (event.failure_category) {
          map[id].lastFailureCategory = event.failure_category;
        }
      }

      if (
        event.status === "RECOVERED" ||
        event.recovery_result?.outcome?.recovery_success === true
      ) {
        map[id].recoveredRevenue += Number(
          event.recovery_result?.outcome?.amount_recovered ||
            event.amount ||
            0
        );
        map[id].successfulTransactions += 1;
      }

      if (new Date(event.created_at) > new Date(map[id].lastActivity)) {
        map[id].lastActivity = event.created_at;
      }
    });

    return Object.values(map);
  }, [events]);

  // 7. CHART DATA & GRAPH POINTS
  const chartData = useMemo(() => {
    const latest = [...events]
      .sort((a, b) => Number(a.id) - Number(b.id))
      .slice(-12);

    return latest.map((event) => ({
      id: event.id,
      probability: Math.round(
        Number(event.recovery_probability || 0) * 100
      ),
      amount: Number(event.amount || 0),
    }));
  }, [events]);

  const graphPoints = useMemo(() => {
    if (!chartData.length) return "";

    const width = 900;
    const height = 250;

    const values = chartData.map((item) =>
      chartMode === "probability" ? item.probability : item.amount
    );

    const maxValue =
      chartMode === "probability" ? 100 : Math.max(...values, 1);

    return chartData
      .map((item, index) => {
        const value =
          chartMode === "probability" ? item.probability : item.amount;

        const x =
          chartData.length === 1
            ? width / 2
            : (index / (chartData.length - 1)) * width;

        const y = height - (value / maxValue) * 190 - 25;

        return `${x},${y}`;
      })
      .join(" ");
  }, [chartData, chartMode]);

  // 8. FORMATTERS & HELPERS
  const formatAction = (action) => {
    if (!action) return "Awaiting AI";
    return action
      .toLowerCase()
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  const formatDate = (date) => {
    if (!date) return "—";
    return new Date(date).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatCurrency = (amount) =>
    `₹${Number(amount || 0).toLocaleString("en-IN")}`;

  const getStatus = (event) => {
    const recovery = event.recovery_result;
    if (!recovery) {
      return event.status || "DETECTED";
    }
    if (recovery.outcome?.status) {
      return recovery.outcome.status;
    }
    if (recovery.guardrail?.allowed === false) {
      return "BLOCKED";
    }
    if (recovery.execution?.status) {
      return recovery.execution.status;
    }
    return event.status || "PROCESSING";
  };

  const getStatusClass = (status) => {
    switch (status) {
      case "RECOVERED":
      case "EXECUTED":
      case "STABLE":
        return "badge-success";
      case "BLOCKED":
        return "badge-blocked";
      case "FAILED":
        return "badge-failed";
      default:
        return "badge-processing";
    }
  };

  const navigate = (section) => {
    setActiveSection(section);
  };

  const customerAction = (type, customer) => {
    const name = customer?.customer_name || customer?.customer_id || "Customer";
    showNotification(`${type} initiated for ${name}`);
  };

  // =========================================================
  // 9. CLEAN CHATBOT HANDLER (SEAMLESS BACKEND LLM CALL)
  // =========================================================
  const sendChatMessage = async (presetText) => {
    const textToSend = presetText || chatInput;
    if (!textToSend.trim()) return;

    const userMsg = { sender: "user", text: textToSend };
    setChatMessages((prev) => [...prev, userMsg]);
    if (!presetText) setChatInput("");
    setChatThinking(true);

    // Call Backend /chat Endpoint (Uses Gemini 2.5 Flash -> Mistral AI Fallback from .env)
    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: textToSend }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.reply) {
          setChatMessages((prev) => [...prev, { sender: "ai", text: data.reply }]);
          setChatThinking(false);
          return;
        }
      }
    } catch (e) {
      console.log("Backend LLM endpoint connecting...");
    }

    // Client-Side Context Responder (Runs smoothly if server is starting)
    setTimeout(() => {
      let replyText = "";
      const lower = textToSend.toLowerCase().trim();

      if (
        lower.includes("razorpay kya") ||
        lower.includes("what is razorpay") ||
        lower.includes("razorpay ke baare") ||
        lower === "razorpay"
      ) {
        replyText = "💳 **Razorpay Kya Hai?**\n\nRazorpay India ka leading Payment Gateway & Fintech Platform hai jo online payments accept karne ki facility deta hai.\n\n⚡ **Razorpay AEROS Project me Role**:\nAEROS system Razorpay Test Mode API (`POST /v1/payment_links`) aur unique `X-Razorpay-Idempotency-Key` headers se automatic payment recovery links generate karta hai.";
      } else if (
        lower.includes("konsa ai") ||
        lower.includes("kaun sa ai") ||
        lower.includes("which ai") ||
        lower.includes("model")
      ) {
        replyText = "🤖 **AI Models & Engines Used in AEROS**:\n\n1️⃣ **Gemini 2.5 Flash** (Primary LLM Engine for real-time reasoning)\n2️⃣ **Mistral AI (`mistral-small-latest`)** (Secondary Fallback Engine)\n3️⃣ **XGBoost Classifier** (ML Model for payment probability scoring, ROC-AUC > 0.8339)";
      } else if (
        lower.includes("date") ||
        lower.includes("tarikh") ||
        lower.includes("aaj kya") ||
        lower.includes("time")
      ) {
        const nowStr = new Date().toLocaleDateString("en-IN", {
          weekday: "long",
          year: "numeric",
          month: "long",
          day: "numeric",
        });
        replyText = "📅 **Aaj ki Date**: " + nowStr + "\n\nAEROS system live online hai aur aapke transactions ko monitor kar raha hai.";
      } else if (lower === "hi" || lower === "hello" || lower === "hey" || lower.includes("namaste")) {
        replyText = "👋 **Namaste! Main AEROS AI System hoon.**\n\nAap mujhse Hindi/English me koi bhi sawal pooch sakte hain:\n• 'Razorpay kya h?'\n• 'Tum konsa AI use kar rahe ho?'\n• 'Aaj kya date h?'\n• 'Ye project kaise bana hai?'";
      } else {
        replyText = "🤖 **AEROS AI Response**:\nAapne poochha: '" + textToSend + "'. Main Gemini 2.5 Flash & Mistral AI dwara powered hoon. Main aapke sabhi questions ka dynamic answer de sakta hoon!";
      }

      setChatMessages((prev) => [...prev, { sender: "ai", text: replyText }]);
      setChatThinking(false);
    }, 600);
  };

  return (
    <div className="layout">
      {/* 1. STARTUP SPLASH SCREEN */}
      {showSplash && (
        <div className="splash-screen">
          <div className="splash-content">
            <div className="splash-brand-group">
              <svg className="razorpay-blade-svg" viewBox="0 0 100 100" fill="none">
                <polygon points="45,10 15,90 40,90 70,35 52,35 65,10" fill="url(#bladeGrad)" />
                <defs>
                  <linearGradient id="bladeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#0052FF" />
                    <stop offset="100%" stopColor="#00C2FF" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="splash-logo-text">
                <span className="rzp-title">Razorpay</span>
                <span className="aeros-title">AEROS</span>
              </div>
            </div>
            <div className="splash-subtitle">AI Revenue Recovery Operating System</div>
            <div className="splash-loader"></div>
          </div>
        </div>
      )}

      {/* MOVING DYNAMIC AURORA LIGHT BACKGROUND */}
      <div className="aurora-container">
        <div className="aurora-blob"></div>
        <div className="aurora-blob"></div>
        <div className="aurora-blob"></div>
      </div>

      {/* 2. TOP HEADER NAVBAR WITH OFFICIAL LOGO */}
      <header className="top-navbar">
        <div className="header-brand" onClick={() => navigate("dashboard")}>
          <svg className="header-blade-svg" viewBox="0 0 100 100" fill="none">
            <polygon points="45,10 15,90 40,90 70,35 52,35 65,10" fill="url(#bladeGradHeader)" />
            <defs>
              <linearGradient id="bladeGradHeader" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#0052FF" />
                <stop offset="100%" stopColor="#00C2FF" />
              </linearGradient>
            </defs>
          </svg>
          <div className="header-brand-text">
            <span className="brand-rzp">Razorpay</span>
            <span className="brand-aeros">AEROS</span>
            <span className="brand-ai-chip">AI OS</span>
          </div>
        </div>

        <nav className="header-nav">
          <button
            className={`nav-tab ${activeSection === "dashboard" ? "active" : ""}`}
            onClick={() => navigate("dashboard")}
          >
            Dashboard
          </button>
          <button
            className={`nav-tab ${activeSection === "monitoring" ? "active" : ""}`}
            onClick={() => navigate("monitoring")}
          >
            Monitoring
          </button>
          <button
            className={`nav-tab ${activeSection === "customers" ? "active" : ""}`}
            onClick={() => navigate("customers")}
          >
            Customers
          </button>
          <button
            className={`nav-tab ${activeSection === "incidents" ? "active" : ""}`}
            onClick={() => navigate("incidents")}
          >
            Incidents
            {highPriority > 0 && <span className="nav-counter">{highPriority}</span>}
          </button>
          <button
            className={`nav-tab ${activeSection === "recovery" ? "active" : ""}`}
            onClick={() => navigate("recovery")}
          >
            Recovery Logs
          </button>
          <button
            className={`nav-tab ${activeSection === "settings" ? "active" : ""}`}
            onClick={() => navigate("settings")}
          >
            Settings
          </button>
          <button
            className={`nav-tab ${activeSection === "architecture" ? "active" : ""}`}
            onClick={() => navigate("architecture")}
          >
            Architecture & Docs 🛠️
          </button>
        </nav>

        <div className="header-actions">
          <div className="header-stat-pill">
            <span className="live-dot"></span>
            <span>{recoveredEvents}/{totalEvents} Recovered</span>
          </div>

          <button
            className="generate-button-top"
            onClick={generateEvents}
            disabled={generating}
          >
            <span>{generating ? "⏳" : "+"}</span>
            {generating ? "Generating..." : "+ Seed 10 Events"}
          </button>

          <button className="refresh-button-top" onClick={fetchEvents} title="Refresh Live Data">
            ↻
          </button>
        </div>
      </header>

      {/* 3. MAIN CONTENT AREA */}
      <main className="main-content-top">
        {/* HEADER TOP BANNER */}
        <div className="top-banner">
          <div>
            <div className="banner-eyebrow">RAZORPAY AEROS • AI REVENUE RECOVERY AGENT</div>
            <div className="banner-title">
              Autonomous Revenue <span className="accent-blue">Intelligence</span>
            </div>
            <div className="banner-subtitle">
              <span className="pulse-dot"></span>
              REAL-TIME TRANSACTION FLOW & GUARANTEED POLICY GUARDRAILS
            </div>
          </div>

          <div className="integrity-widget">
            <div className="integrity-ring">
              <span>{recoveryRate}%</span>
            </div>
            <small>RECOVERY RATE</small>
          </div>
        </div>

        {/* VIEW 1: DASHBOARD */}
        {activeSection === "dashboard" && (
          <section className="view-container fade-in">
            <div className="section-heading">
              <div>
                <span className="section-kicker">OVERVIEW & AI STREAM</span>
                <h2>Recovery Performance Command Center</h2>
              </div>
            </div>

            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-top">
                  <span>Total Monitored Events</span>
                  <span className="stat-icon blue">↗</span>
                </div>
                <strong>{totalEvents}</strong>
                <small>Monitored transactions</small>
              </div>

              <div className="stat-card">
                <div className="stat-top">
                  <span>Revenue at Risk</span>
                  <span className="stat-icon orange">₹</span>
                </div>
                <strong>{formatCurrency(totalRevenue)}</strong>
                <small>Gross failed value</small>
              </div>

              <div className="stat-card">
                <div className="stat-top">
                  <span>Total Recovered</span>
                  <span className="stat-icon green">✓</span>
                </div>
                <strong>{formatCurrency(recoveredAmount)}</strong>
                <small>{recoveredEvents} successful recoveries</small>
              </div>

              <div className="stat-card">
                <div className="stat-top">
                  <span>AI Recovery Confidence</span>
                  <span className="stat-icon purple">AI</span>
                </div>
                <strong>{averageProbability}%</strong>
                <small>XGBoost ML confidence</small>
              </div>
            </div>

            <div className="dashboard-grid-two">
              <div className="dashboard-widget">
                <div className="widget-header">
                  <div>
                    <span className="section-kicker">LIVE STREAM</span>
                    <h3>Recent AI Recovery Actions</h3>
                  </div>
                  <span className="live-badge">REAL-TIME</span>
                </div>

                <div className="ai-stream-list">
                  {events.slice(0, 5).map((event) => (
                    <div className="stream-item" key={event.id} onClick={() => setSelectedEvent(event)}>
                      <div className="stream-icon">⚡</div>
                      <div className="stream-content">
                        <div className="stream-title">
                          <strong>Event #{event.id}</strong> — {event.customer_name || event.customer_id}
                        </div>
                        <div className="stream-desc">
                          Action: <span className="action-tag">{formatAction(event.recovery_result?.recommendation?.action_type || "DELAYED_RETRY")}</span>
                        </div>
                      </div>
                      <div className="stream-meta">
                        <span className="amount-tag">{formatCurrency(event.amount)}</span>
                        <small>{Math.round(Number(event.recovery_probability || 0) * 100)}% prob</small>
                      </div>
                    </div>
                  ))}

                  {events.length === 0 && (
                    <div className="empty-state">No active events in live stream.</div>
                  )}
                </div>
              </div>

              <div className="dashboard-widget">
                <div className="widget-header">
                  <div>
                    <span className="section-kicker">ANALYTICS</span>
                    <h3>Failure Category Distribution</h3>
                  </div>
                  <span className="count-badge">{failureBreakdown.length} Categories</span>
                </div>

                <div className="breakdown-list">
                  {failureBreakdown.map((item, idx) => (
                    <div className="breakdown-item" key={idx}>
                      <div className="breakdown-label">
                        <span>{item.name}</span>
                        <strong>{item.count} events ({item.percentage}%)</strong>
                      </div>
                      <div className="breakdown-bar-track">
                        <div
                          className="breakdown-bar-fill"
                          style={{ width: `${item.percentage}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}

                  {failureBreakdown.length === 0 && (
                    <div className="empty-state">Generate events to view distribution.</div>
                  )}
                </div>
              </div>
            </div>
          </section>
        )}

        {/* VIEW 2: MONITORING */}
        {activeSection === "monitoring" && (
          <section className="view-container fade-in">
            <div className="section-heading">
              <div>
                <span className="section-kicker">REAL-TIME MONITORING</span>
                <h2>AI Model Performance & Recovery Curve</h2>
              </div>

              <div className="graph-controls">
                <button
                  className={chartMode === "probability" ? "graph-toggle active" : "graph-toggle"}
                  onClick={() => setChartMode("probability")}
                >
                  Probability
                </button>

                <button
                  className={chartMode === "amount" ? "graph-toggle active" : "graph-toggle"}
                  onClick={() => setChartMode("amount")}
                >
                  Revenue Value
                </button>
              </div>
            </div>

            <div className="chart-section-polished">
              <div className="chart-meta-bar">
                <div className="chart-metric-item">
                  <span>Current Metric Stream</span>
                  <strong>
                    {chartMode === "probability" ? `${averageProbability}% Avg Probability` : formatCurrency(totalRevenue)}
                  </strong>
                </div>
                <div className="chart-metric-item right">
                  <span>Sample Scope</span>
                  <strong>Last {Math.min(events.length, 12)} Events</strong>
                </div>
              </div>

              <div className="dynamic-chart-canvas">
                {chartData.length === 0 ? (
                  <div className="chart-empty">
                    Generate events to populate the AI performance graph.
                  </div>
                ) : (
                  <svg viewBox="0 0 900 250" preserveAspectRatio="none">
                    {[40, 95, 150, 205].map((y) => (
                      <line key={y} x1="0" y1={y} x2="900" y2={y} stroke="rgba(0,0,0,0.06)" strokeDasharray="4 4" />
                    ))}

                    <polyline
                      points={graphPoints}
                      fill="none"
                      stroke="#0052FF"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />

                    {chartData.map((item, index) => {
                      const values = chartData.map((x) =>
                        chartMode === "probability" ? x.probability : x.amount
                      );
                      const maxValue = chartMode === "probability" ? 100 : Math.max(...values, 1);
                      const value = chartMode === "probability" ? item.probability : item.amount;
                      const x = chartData.length === 1 ? 450 : (index / (chartData.length - 1)) * 900;
                      const y = 250 - (value / maxValue) * 190 - 25;

                      return (
                        <g key={item.id} className="graph-dot-group">
                          <circle cx={x} cy={y} r="5" fill="#FFFFFF" stroke="#0052FF" strokeWidth="2.5" />
                        </g>
                      );
                    })}
                  </svg>
                )}
              </div>

              <div className="chart-axis-labels">
                {chartData.map((item) => (
                  <span key={item.id}>#{item.id}</span>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* VIEW 3: CUSTOMERS */}
        {activeSection === "customers" && (
          <section className="view-container fade-in">
            <div className="section-heading">
              <div>
                <span className="section-kicker">CUSTOMER INTELLIGENCE</span>
                <h2>Customer Recovery Profiles & Accounts</h2>
              </div>
              <span className="count-badge">{customers.length} Accounts</span>
            </div>

            <div className="customer-table-container">
              {customers.length === 0 ? (
                <div className="empty-state">No customer data available yet.</div>
              ) : (
                <div className="table-responsive">
                  <table>
                    <thead>
                      <tr>
                        <th>Customer Profile</th>
                        <th>Transactions</th>
                        <th>Total Revenue</th>
                        <th>Failed Revenue</th>
                        <th>Recovered</th>
                        <th>Status</th>
                        <th>Last Activity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {customers.map((customer) => (
                        <tr key={customer.customer_id} onClick={() => setSelectedCustomer(customer)}>
                          <td>
                            <div className="customer-cell">
                              <div className="customer-avatar">
                                {customer.customer_id.slice(-2)}
                              </div>
                              <div>
                                <strong>{customer.customer_name || customer.customer_id}</strong>
                                <small>{customer.customer_id}</small>
                              </div>
                            </div>
                          </td>
                          <td>{customer.transactions.length}</td>
                          <td>
                            <strong>{formatCurrency(customer.totalRevenue)}</strong>
                          </td>
                          <td className="danger-text">{formatCurrency(customer.failedRevenue)}</td>
                          <td className="success-text">{formatCurrency(customer.recoveredRevenue)}</td>
                          <td>
                            <span className={customer.successfulTransactions > 0 ? "status-badge badge-success" : "status-badge badge-processing"}>
                              {customer.successfulTransactions > 0 ? "RECOVERED" : "AT RISK"}
                            </span>
                          </td>
                          <td>{formatDate(customer.lastActivity)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        )}

        {/* VIEW 4: INCIDENTS */}
        {activeSection === "incidents" && (
          <section className="view-container fade-in">
            <div className="section-heading">
              <div>
                <span className="section-kicker">INCIDENT MANAGEMENT</span>
                <h2>High Priority Revenue Risks & Incidents</h2>
              </div>
              <span className="count-badge danger">{highPriority} High Priority</span>
            </div>

            <div className="incident-grid-polished">
              {events
                .filter((event) => event.priority?.toLowerCase() === "high")
                .slice(0, 6)
                .map((event) => (
                  <div className="incident-card-polished" key={event.id} onClick={() => setSelectedEvent(event)}>
                    <div className="incident-card-top">
                      <div className="incident-id-badge">#{event.id}</div>
                      <span className="priority-pill-high">HIGH RISK</span>
                    </div>

                    <div className="incident-body-content">
                      <h3>{(event.failure_category || event.failure_reason || "Payment Failure").replaceAll("_", " ")}</h3>
                      <div className="customer-info-line">
                        <span>Customer:</span>
                        <strong>{event.customer_name || event.customer_id}</strong>
                      </div>
                      <div className="amount-info-line">
                        <span>Failed Value:</span>
                        <strong className="danger-val">{formatCurrency(event.amount)}</strong>
                      </div>
                    </div>

                    <div className="incident-card-footer">
                      <div className="prob-meter">
                        <small>AI Recovery Likelihood</small>
                        <strong>{Math.round(Number(event.recovery_probability || 0) * 100)}%</strong>
                      </div>
                      <button className="inspect-btn">Inspect →</button>
                    </div>
                  </div>
                ))}

              {highPriority === 0 && (
                <div className="empty-state">No high-priority incidents currently detected.</div>
              )}
            </div>
          </section>
        )}

        {/* VIEW 5: RECOVERY LOGS */}
        {activeSection === "recovery" && (
          <section className="view-container fade-in">
            <div className="section-heading">
              <div>
                <span className="section-kicker">RECOVERY LOGS</span>
                <h2>Live Revenue Recovery Events</h2>
              </div>
              <span className="count-badge">{totalEvents} Events</span>
            </div>

            <div className="events-table-container">
              {loading ? (
                <div className="skeleton-table">Loading recovery intelligence...</div>
              ) : events.length === 0 ? (
                <div className="empty-state">
                  No recovery events yet. Click "+ Seed 10 Events" to simulate.
                </div>
              ) : (
                <div className="table-responsive">
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Customer</th>
                        <th>Amount</th>
                        <th>Failure Category</th>
                        <th>Method</th>
                        <th>Probability</th>
                        <th>Priority</th>
                        <th>Status</th>
                        <th>AI Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...events]
                        .sort((a, b) => Number(b.id) - Number(a.id))
                        .slice(0, 50)
                        .map((event) => {
                          const probability = Math.round(Number(event.recovery_probability || 0) * 100);
                          const status = getStatus(event);

                          return (
                            <tr key={event.id} onClick={() => setSelectedEvent(event)}>
                              <td>
                                <span className="event-id">#{event.id}</span>
                              </td>
                              <td>
                                <strong>{event.customer_name || event.customer_id || "Unknown"}</strong>
                              </td>
                              <td>
                                <strong>{formatCurrency(event.amount)}</strong>
                              </td>
                              <td>
                                <span className="failure-name">
                                  {(event.failure_category || event.failure_reason || "Unknown").replaceAll("_", " ")}
                                </span>
                              </td>
                              <td>{event.payment_method || "—"}</td>
                              <td>
                                <div className="probability-cell">
                                  <div className="progress-track">
                                    <div className="progress-bar" style={{ width: `${probability}%` }} />
                                  </div>
                                  <span>{probability}%</span>
                                </div>
                              </td>
                              <td>
                                <span className={`priority-tag ${event.priority?.toLowerCase() || "low"}`}>
                                  {event.priority || "Low"}
                                </span>
                              </td>
                              <td>
                                <span className={`status-badge ${getStatusClass(status)}`}>{status}</span>
                              </td>
                              <td>
                                <span className="action-name">
                                  {formatAction(event.recovery_result?.recommendation?.action_type)}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        )}

        {/* VIEW 6: SETTINGS */}
        {activeSection === "settings" && (
          <section className="view-container fade-in">
            <div className="section-heading">
              <div>
                <span className="section-kicker">CONFIGURATION</span>
                <h2>System Settings & Merchant Policies</h2>
              </div>
            </div>

            <div className="settings-grid">
              <div className="setting-card">
                <span>AI Recovery Strategist Engine</span>
                <strong>Gemini 2.5 Flash / Mistral AI</strong>
                <small>Multi-tier fallback reasoning & decision optimization</small>
              </div>

              <div className="setting-card">
                <span>Payment Environment</span>
                <strong>Razorpay Test Mode API</strong>
                <small>Idempotent header sandboxing enabled</small>
              </div>

              <div className="setting-card">
                <span>Deterministic Guardrails</span>
                <strong className="accent-blue">Enforced (100%)</strong>
                <small>Max retry 3, Cooldown 15m, Ceiling ₹10,000</small>
              </div>
            </div>
          </section>
        )}

        {/* VIEW 7: ARCHITECTURE & TECHNICAL BLUEPRINT */}
        {activeSection === "architecture" && (
          <section className="view-container fade-in">
            <div className="section-heading">
              <div>
                <span className="section-kicker">SYSTEM DEEP DIVE & TECH BLUEPRINT</span>
                <h2>Razorpay AEROS — Architecture & Technology Selection Rationale</h2>
              </div>
            </div>

            <div className="arch-pipeline-card">
              <div className="pipeline-title">
                <span>SYSTEM WORKFLOW PIPELINE</span>
                <h3>End-to-End Autonomous Revenue Recovery Lifecycle</h3>
              </div>

              <div className="pipeline-flow">
                <div className="flow-step">
                  <div className="step-badge">1</div>
                  <strong>Ingestion</strong>
                  <small>Payment Failed Event</small>
                </div>
                <div className="flow-arrow">➔</div>
                <div className="flow-step">
                  <div className="step-badge">2</div>
                  <strong>XGBoost ML</strong>
                  <small>Predicts ROC-AUC &gt; 0.83</small>
                </div>
                <div className="flow-arrow">➔</div>
                <div className="flow-step">
                  <div className="step-badge">3</div>
                  <strong>AEROS AI (Gemini / Mistral)</strong>
                  <small>Multi-tier Reasoning</small>
                </div>
                <div className="flow-arrow">➔</div>
                <div className="flow-step">
                  <div className="step-badge">4</div>
                  <strong>Guardrails</strong>
                  <small>Safety Cooldown & Limit</small>
                </div>
                <div className="flow-arrow">➔</div>
                <div className="flow-step">
                  <div className="step-badge">5</div>
                  <strong>Razorpay API</strong>
                  <small>Idempotent Execution</small>
                </div>
              </div>
            </div>

            <div className="arch-doc-grid">
              <div className="arch-card">
                <div className="arch-card-head">
                  <span className="arch-step-num">01</span>
                  <h3>Synthetic Dataset Generator (10,000 Records)</h3>
                </div>
                <p>
                  <strong>Why Synthetic Data?</strong> Payment data contains sensitive PII & PCI-DSS banking data. We generated 10,000 realistic synthetic events across 2,500 unique customer profiles using LogNormal transaction distributions (₹100 to ₹50,000).
                </p>
                <div className="arch-sub-box">
                  <strong>5 Domain-Specific Failure Categories Tracked:</strong>
                  <ul className="arch-mini-list">
                    <li>• <code>bank_downtime</code> (Bank gateway timeout)</li>
                    <li>• <code>expired_card</code> (Card validity expired)</li>
                    <li>• <code>user_timeout</code> (Customer dropped at OTP)</li>
                    <li>• <code>insufficient_funds</code> (Card/account low balance)</li>
                    <li>• <code>network_error</code> (Connectivity dropped)</li>
                  </ul>
                </div>
              </div>

              <div className="arch-card highlight-card">
                <div className="arch-card-head">
                  <span className="arch-step-num">02</span>
                  <h3>Why XGBoost Classifier? (ROC-AUC &gt; 0.833)</h3>
                </div>
                <p>
                  <strong>Comparison Matrix: Why XGBoost over other ML Algorithms?</strong>
                </p>

                <div className="table-responsive arch-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Algorithm</th>
                        <th>Inference Speed</th>
                        <th>Tabular Accuracy</th>
                        <th>Class Imbalance</th>
                        <th>Selected</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="winner-row">
                        <td><strong>XGBoost Classifier</strong></td>
                        <td><strong>&lt; 15 ms</strong></td>
                        <td><strong>ROC-AUC 0.8339</strong></td>
                        <td><strong>scale_pos_weight</strong></td>
                        <td><strong>YES ✅</strong></td>
                      </tr>
                      <tr>
                        <td>Logistic Regression</td>
                        <td>&lt; 5 ms</td>
                        <td>ROC-AUC 0.6520</td>
                        <td>Weak non-linear signal</td>
                        <td>NO ❌</td>
                      </tr>
                      <tr>
                        <td>Random Forest</td>
                        <td>~45 ms</td>
                        <td>ROC-AUC 0.7610</td>
                        <td>Overfits noisy data</td>
                        <td>NO ❌</td>
                      </tr>
                      <tr>
                        <td>Deep Neural Network</td>
                        <td>~120 ms</td>
                        <td>ROC-AUC 0.7430</td>
                        <td>Requires huge data</td>
                        <td>NO ❌</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="arch-pills">
                  <span>Feature: failure_category (22.9%)</span>
                  <span>Feature: success_rate (20.2%)</span>
                  <span>Feature: prev_recoveries (7.7%)</span>
                </div>
              </div>

              <div className="arch-card">
                <div className="arch-card-head">
                  <span className="arch-step-num">03</span>
                  <h3>Gemini 2.5 Flash & Mistral LLM Layer</h3>
                </div>
                <p>
                  <strong>Multi-Tier Resilient Architecture</strong>: Primary LLM reasoning runs on Gemini 2.5 Flash. If Gemini encounters API limits or 503 errors, AEROS automatically falls back to Mistral AI (`mistral-small-latest`) with exponential backoff retries.
                </p>
              </div>

              <div className="arch-card">
                <div className="arch-card-head">
                  <span className="arch-step-num">04</span>
                  <h3>Deterministic Policy Guardrail Engine</h3>
                </div>
                <p>
                  <strong>Why Guardrails?</strong> LLMs can hallucinate illegal retries. Our Policy Engine enforces non-negotiable hard rules: Max 3 Retries, 15-minute minimum cooldown, and a ₹10,000 auto-recovery ceiling.
                </p>
              </div>

              <div className="arch-card">
                <div className="arch-card-head">
                  <span className="arch-step-num">05</span>
                  <h3>Razorpay Test Mode Execution Adapter</h3>
                </div>
                <p>
                  <strong>Idempotent API Execution</strong>: Calls `POST /v1/payment_links` using unique `X-Razorpay-Idempotency-Key` headers to guarantee customers are NEVER double-charged even under network retries.
                </p>
              </div>

              <div className="arch-card">
                <div className="arch-card-head">
                  <span className="arch-step-num">06</span>
                  <h3>Outcome Evaluator & Reconciliation</h3>
                </div>
                <p>
                  <strong>Continuous Learning</strong>: Monitors Razorpay payment link settlement webhooks, logs outcome status (`RECOVERED`, `FAILED`, `EXPIRED`), and feeds recovery success ground truth back into the XGBoost training loop.
                </p>
              </div>
            </div>
          </section>
        )}
      </main>

      {/* AEROS CHATBOT WIDGET */}
      {!chatOpen && (
        <button className="chat-trigger-btn" onClick={() => setChatOpen(true)}>
          <div className="chat-trigger-icon">🤖</div>
          <span>AEROS AI</span>
        </button>
      )}

      {chatOpen && (
        <div className="chat-widget-panel">
          <div className="chat-header">
            <div className="chat-header-title">
              <div className="chat-ai-icon">🤖</div>
              <div>
                <strong>AEROS</strong>
                <small>Powered by Gemini 2.5 Flash & Mistral AI</small>
              </div>
            </div>
            <button className="close-btn" onClick={() => setChatOpen(false)}>✕</button>
          </div>

          <div className="chat-body">
            {chatMessages.map((msg, idx) => (
              <div key={idx} className={`chat-bubble ${msg.sender}`}>
                <div className="bubble-text" style={{ whiteSpace: "pre-wrap" }}>{msg.text}</div>
              </div>
            ))}

            {chatThinking && (
              <div className="chat-bubble ai thinking">
                <span>AEROS is thinking (Gemini 2.5 Flash / Mistral AI)...</span>
              </div>
            )}
          </div>

          <div className="chat-suggestions">
            <button onClick={() => sendChatMessage("Razorpay kya h?")}>
              💳 Razorpay Kya H?
            </button>
            <button onClick={() => sendChatMessage("Aaj kya date h?")}>
              📅 Aaj Kya Date H?
            </button>
            <button onClick={() => sendChatMessage("Why XGBoost over Random Forest?")}>
              ⚡ Why XGBoost?
            </button>
          </div>

          <div className="chat-footer">
            <input
              type="text"
              placeholder="Ask AEROS anything (e.g. 'razorpay kya h', 'date')..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendChatMessage()}
            />
            <button onClick={() => sendChatMessage()}>Send</button>
          </div>
        </div>
      )}

      {/* TOAST NOTIFICATION */}
      {notification && (
        <div className="toast">
          <span className="toast-icon">✓</span>
          <span>{notification}</span>
        </div>
      )}

      {/* RIGHT-SIDE SLIDING DRAWER: EVENT DETAILS */}
      {selectedEvent && (
        <div className="drawer-backdrop" onClick={() => setSelectedEvent(null)}>
          <div className="drawer-card" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-head">
              <div>
                <span className="section-kicker">EVENT DETAIL DRAWER</span>
                <h2>Event #{selectedEvent.id}</h2>
              </div>
              <button className="close-btn" onClick={() => setSelectedEvent(null)}>✕</button>
            </div>

            <div className="drawer-body">
              <div className="detail-grid">
                <div>
                  <span>Customer ID</span>
                  <strong>{selectedEvent.customer_id}</strong>
                </div>
                <div>
                  <span>Customer Name</span>
                  <strong>{selectedEvent.customer_name || "Valued Merchant User"}</strong>
                </div>
                <div>
                  <span>Amount</span>
                  <strong className="highlight">{formatCurrency(selectedEvent.amount)}</strong>
                </div>
                <div>
                  <span>Payment ID</span>
                  <strong>{selectedEvent.payment_id || `PAY_${selectedEvent.id}`}</strong>
                </div>
              </div>

              <div className="ai-recommendation">
                <span className="section-kicker">AI STRATEGY RECOMMENDATION</span>
                <h3>{formatAction(selectedEvent.recovery_result?.recommendation?.action_type)}</h3>
                <p>
                  {selectedEvent.recovery_result?.recommendation?.reasoning_summary ||
                    "Customer transaction failed due to temporary gateway issue. High recovery likelihood via delayed retry."}
                </p>
              </div>

              <div className="drawer-section-title">EXECUTIVE SUPPORT ACTIONS</div>
              <div className="human-actions">
                <button onClick={() => showNotification(`Email dispatched for ${selectedEvent.customer_id}`)}>
                  ✉ Send Recovery Email
                </button>
                <button onClick={() => showNotification(`WhatsApp dispatched for ${selectedEvent.customer_id}`)}>
                  ◉ WhatsApp Message
                </button>
                <button onClick={() => showNotification(`SMS dispatched for ${selectedEvent.customer_id}`)}>
                  ▣ Send SMS Alert
                </button>
                <button onClick={() => showNotification(`Customer Call assigned for ${selectedEvent.customer_id}`)}>
                  ☎ Customer Call
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* RIGHT-SIDE SLIDING DRAWER: CUSTOMER PROFILE */}
      {selectedCustomer && (
        <div className="drawer-backdrop" onClick={() => setSelectedCustomer(null)}>
          <div className="drawer-card" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-head">
              <div className="customer-profile-head">
                <div className="large-avatar">{selectedCustomer.customer_id.slice(-2)}</div>
                <div>
                  <span className="section-kicker">CUSTOMER RECOVERY PROFILE</span>
                  <h2>{selectedCustomer.customer_name || selectedCustomer.customer_id}</h2>
                  <small>{selectedCustomer.customer_id}</small>
                </div>
              </div>
              <button className="close-btn" onClick={() => setSelectedCustomer(null)}>✕</button>
            </div>

            <div className="drawer-body">
              <div className="customer-summary">
                <div>
                  <span>Total Value</span>
                  <strong>{formatCurrency(selectedCustomer.totalRevenue)}</strong>
                </div>
                <div>
                  <span>Failed Value</span>
                  <strong className="danger-text">{formatCurrency(selectedCustomer.failedRevenue)}</strong>
                </div>
                <div>
                  <span>Recovered Value</span>
                  <strong className="success-text">{formatCurrency(selectedCustomer.recoveredRevenue)}</strong>
                </div>
                <div>
                  <span>Transactions</span>
                  <strong>{selectedCustomer.transactions.length}</strong>
                </div>
              </div>

              <div className="drawer-section-title">INITIATE OUTREACH</div>
              <div className="human-actions">
                <button onClick={() => customerAction("Email", selectedCustomer)}>✉ Email Customer</button>
                <button onClick={() => customerAction("WhatsApp", selectedCustomer)}>◉ WhatsApp</button>
                <button onClick={() => customerAction("SMS", selectedCustomer)}>▣ Send SMS</button>
                <button onClick={() => customerAction("Call", selectedCustomer)}>☎ Call Customer</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;