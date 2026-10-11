
import { useEffect, useState } from "react";
import "./App.css";

import "./App.css";

const API_URL = "http://127.0.0.1:8000";

// ================= APP ROUTING =================

function App() {
  return window.location.pathname === "/admin"
    ? <AdminDashboard />
    : <StudentPage />;
}

// ================= STUDENT PAGE =================

function StudentPage() {
  const [ticket, setTicket] = useState("");
  const [messages, setMessages] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showDetails, setShowDetails] = useState(false);
  const [details, setDetails] = useState({
    transaction_id: "",
    date: "",
    amount: "",
    registered_contact: "",
    batch_name: "",
    device: "",
    issue_details: "",
  });
  const [submitted, setSubmitted] = useState(null);
  const [successNotice, setSuccessNotice] = useState("");
  const [finished, setFinished] = useState(false);

  const latestText = messages.length ? messages[messages.length - 1].content : "";
  const categoryText = `${(result?.categories || []).join(" ")} ${result?.category || ""} ${ticket}`.toLowerCase();
  const isAcademic = categoryText.includes("academic_doubt") || categoryText.includes("academic doubt") || /math|physics|chemistry|gradient descent|explain this concept|homework|study doubt/.test(categoryText);
  const isPayment = /payment|paid|transaction|charged|bank|order confirmation/.test(categoryText);
  const isRefund = /refund/.test(categoryText);
  const isBatch = /batch_access|batch access|batch|course access/.test(categoryText);
  const isTechnical = /technical|app crash|crash|error|login|website|app/.test(categoryText);
  const isFee = /fee_structure|fee structure|fees|fee/.test(categoryText);

  function addMessage(role, content) {
    setMessages((previous) => [...previous, { role, content }]);
  }

  async function askAgent(currentTicket, history, attempt = 1) {
    const response = await fetch(`${API_URL}/tickets/follow-up`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ticket: currentTicket,
        conversation_history: history,
        attempt_number: Math.min(attempt, 3),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not get an AI response.");
    return data;
  }

  async function submitTicket(e) {
    e.preventDefault();
    const cleanTicket = ticket.trim();
    if (cleanTicket.length < 5) {
      setError("Please describe your question in at least 5 characters.");
      return;
    }

    setLoading(true);
    setError("");
    setMessages([{ role: "student", content: cleanTicket }]);
    setResult(null);
    setSubmitted(null);
    setFinished(false);

    try {
      const data = await askAgent(cleanTicket, [], 1);
      setResult(data);
      setMessages((previous) => [...previous, { role: "assistant", content: data.draft_reply || "I understand. Could you share a little more detail so I can help?" }]);
    } catch (err) {
      setError(err.message === "Failed to fetch" ? "Backend connection failed. Please check that FastAPI is running." : err.message);
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }

  async function continueConversation(buttonText) {
    if (loading) return;
    setError("");
    if (buttonText === "I'm Satisfied") {
      addMessage("student", buttonText);
      addMessage("assistant", "Glad I could help! 😊 You can ask another question whenever you need.");
      setFinished(true);
      return;
    }
    if (buttonText === "Submit Details" || buttonText === "Submit Payment Details" || buttonText === "Submit Refund Request" || buttonText === "Submit Issue Details" || buttonText === "Submit Batch Details") {
      setShowDetails(true);
      return;
    }
    if (buttonText === "Cancel Request") {
      addMessage("student", buttonText);
      addMessage("assistant", "No problem. Your support request has not been submitted. You can continue asking questions or start a new one.");
      return;
    }

    // PAYMENT WORKFLOW: do not call the LLM again and repeat the same questions.
    // Move directly to the explicit payment-details button after troubleshooting fails.
    if (buttonText === "I Still Need Help" && isPayment) {
      setMessages((previous) => [
        ...previous,
        {
          role: "student",
          content: "I tried the troubleshooting steps, but my issue is still unresolved.",
        },
        {
          role: "assistant",
          content: "Sorry the troubleshooting did not resolve the issue. Please select ‘Submit Payment Details’ below to open the support form. Your ticket will be saved only after you submit that form.",
        },
      ]);
      return;
    }

    const studentMessage = buttonText === "Explain Again"
      ? "Please explain that in a different, simpler way."
      : buttonText === "Ask a Follow-up"
        ? "I have a follow-up question. Please invite me to ask it."
        : buttonText === "Try Troubleshooting"
          ? "Please guide me through troubleshooting steps before collecting support details."
          : buttonText === "Understand Refund Policy"
            ? "Please explain the applicable refund policy using the knowledge base."
            : buttonText === "View Fee Information"
              ? "Please explain the available fee information using the knowledge base."
              : buttonText === "Troubleshoot Access"
                  ? "Please help me troubleshoot my batch access issue first."
                  : buttonText === "I Still Need Help"
                    ? "I tried the troubleshooting steps, but they did not work. Please let me submit my payment details for support."
                    : buttonText === "I Have Another Question" || buttonText === "I Need More Help"
                      ? "The issue is still unresolved. Please help me with the next step."
                      : buttonText;

    const history = [...messages, { role: "student", content: studentMessage }];
    setMessages(history);
    setLoading(true);
    try {
      const data = await askAgent(ticket, history, history.filter((m) => m.role === "student").length);
      setResult(data);
      setMessages((previous) => [...previous, { role: "assistant", content: data.draft_reply || "Could you share a little more detail?" }]);
    } catch (err) {
      setError(err.message || "Could not continue the conversation.");
    } finally {
      setLoading(false);
    }
  }

  async function sendChatMessage(e) {
    e.preventDefault();
    const input = e.currentTarget.elements.chatMessage;
    const text = input.value.trim();
    if (!text || loading) return;
    input.value = "";
    const history = [...messages, { role: "student", content: text }];
    setMessages(history);
    setLoading(true);
    setError("");
    try {
      const data = await askAgent(ticket, history, history.filter((m) => m.role === "student").length);
      setResult(data);
      setMessages((previous) => [...previous, { role: "assistant", content: data.draft_reply || "Thanks for the details. Could you clarify one thing?" }]);
    } catch (err) {
      setError(err.message || "Could not send your message.");
    } finally {
      setLoading(false);
    }
  }

  async function submitDetails(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const detailLines = Object.entries(details)
      .filter(([, value]) => value.trim())
      .map(([key, value]) => `${key.replaceAll("_", " ")}: ${value.trim()}`);
    const finalTicket = `${ticket}\n\nStudent-provided support details:\n${detailLines.join("\n")}\n\nConversation history:\n${messages.map((m) => `${m.role}: ${m.content}`).join("\n")}`;

    try {
      // Save only when the student explicitly submits the details.
      const response = await fetch(`${API_URL}/tickets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticket: finalTicket }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Ticket submission failed.");
      // Confirm the save, clear the completed conversation, and return to the original
      // student-support screen so the student can start a fresh chat.
      setSuccessNotice(`Thank you! We have saved your support request successfully. Your ticket ID is #${data.ticket_id}. Please keep this ID for reference.`);
      setMessages([]);
      setTicket("");
      setResult(null);
      setShowDetails(false);
      setSubmitted(null);
      setFinished(false);
      setDetails({ transaction_id: "", date: "", amount: "", registered_contact: "", batch_name: "", device: "", issue_details: "" });
    } catch (err) {
      setError(err.message === "Failed to fetch" ? "Backend connection failed. Please check that FastAPI is running." : err.message);
    } finally {
      setLoading(false);
    }
  }

  function resetChat() {
    setTicket(""); setMessages([]); setResult(null); setError(""); setShowDetails(false); setSubmitted(null); setSuccessNotice(""); setFinished(false);
    setDetails({ transaction_id: "", date: "", amount: "", registered_contact: "", batch_name: "", device: "", issue_details: "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function getButtons() {
    if (finished || submitted) return [];

    // Count student messages: initial complaint = 1, first follow-up = 2,
    // second follow-up = 3. Payment details are shown only after that.
    const studentTurns = messages.filter((message) => message.role === "student").length;

    if (isAcademic) return ["I'm Satisfied", "Explain Again", "Ask a Follow-up"];

    if (isPayment) {
      // After the student says troubleshooting did not help, show only the form action.
      // This prevents the chat from looping and asking for the same details again.
      if (studentTurns >= 2) {
        return ["Submit Payment Details"];
      }
      return ["I Still Need Help", "I Have Another Question"];
    }

    if (isRefund) {
  const studentMessages = messages.filter(
    (message) => message.role === "student"
  );

  const refundRequestStarted = studentMessages.some((message) =>
    /submit refund request|submit batch change request|proceed with my refund|proceed with a batch change|i want to proceed/i.test(
      message.content
    )
  );

  if (refundRequestStarted) {
    return [
      "Submit Refund Request",
      "I Have Another Question",
      "Cancel Request",
    ];
  }

  return [
    "Understand Refund Policy",
    "Submit Refund Request",
    "I Have Another Question",
  ];
}

    if (isBatch) {
      return studentTurns >= 3
        ? ["Troubleshoot Access", "Submit Batch Details", "I Need More Help"]
        : ["Troubleshoot Access", "I Have Another Question"];
    }

    if (isTechnical) {
      return studentTurns >= 3
        ? ["Try Troubleshooting", "Submit Issue Details", "I Need More Help"]
        : ["Try Troubleshooting", "I Have Another Question"];
    }

    if (isFee) return ["View Fee Information", "Ask a Follow-up", "I Need More Help"];

    return studentTurns >= 3
      ? ["Ask a Follow-up", "I Need More Help", "Submit Details"]
      : ["Ask a Follow-up", "I Have Another Question"];
  }

  const sources = result?.sources || [];
  const readableSource = (source) => {
    const name = String(source).split(/[\\/]/).pop().replace(/\.md$/i, "").replaceAll("_", " ");
    return name.replace(/\b\w/g, (char) => char.toUpperCase());
  };

  return (
    <div className="app">
      <header className="header">
        <div className="logo">AI</div>
        <div><h1>PW Student Support</h1><p>AI-powered support assistant</p></div>
        <a className="admin-link" href="/admin">Admin Dashboard →</a>
      </header>

      <main className="container" style={{ maxWidth: 850 }}>
        <section className="intro" style={{ marginBottom: 16 }}>
          <span className="eyebrow">STUDENT SUPPORT</span>
          <h2>How can we help?</h2>
          <p>Ask a question and we'll work through it with you.</p>
        </section>

        {successNotice && (
          <div role="status" style={{ marginBottom: 14, padding: "14px 16px", border: "1px solid #b7e4c7", borderRadius: 12, background: "#effaf2", color: "#185c2b" }}>
            <strong>Thank you!</strong>
            <p style={{ margin: "6px 0 0" }}>{successNotice}</p>
            <button type="button" className="details-button" style={{ marginTop: 10 }} onClick={() => setSuccessNotice("")}>Dismiss</button>
          </div>
        )}

        {!messages.length && !finished && (
          <section className="panel" style={{ padding: 16 }}>
            <form onSubmit={submitTicket}>
              <label htmlFor="ticket">Your question</label>
              <textarea id="ticket" value={ticket} onChange={(e) => setTicket(e.target.value)} placeholder="Describe your question or issue..." rows={3} required />
              <div className="form-footer"><span>{ticket.length} characters</span><button type="submit" disabled={loading}>{loading ? "Thinking..." : "Send message →"}</button></div>
            </form>
          </section>
        )}

        {!!messages.length && (
          <section className="panel" style={{ padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 12 }}>
              <strong>Support chat</strong>
              <button type="button" className="details-button" onClick={resetChat}>New chat</button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {messages.map((message, index) => (
                <div key={`${index}-${message.role}`} style={{ alignSelf: message.role === "student" ? "flex-end" : "flex-start", maxWidth: "88%", padding: "10px 13px", borderRadius: 14, background: message.role === "student" ? "#e7f0ff" : "#f3f5f7", color: "#202733", whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
                  <small style={{ display: "block", fontWeight: 700, marginBottom: 4, opacity: 0.7 }}>{message.role === "student" ? "You" : "AI Support"}</small>
                  {message.content}
                </div>
              ))}
            </div>

            {loading && <p style={{ margin: "12px 0", fontSize: 14 }}>AI is thinking...</p>}

            {!finished && !submitted && !showDetails && (
              <>
                <form onSubmit={sendChatMessage} style={{ display: "flex", gap: 8, marginTop: 14 }}>
                  <input name="chatMessage" aria-label="Message" placeholder="Write a follow-up message..." style={{ flex: 1, minWidth: 0 }} disabled={loading} />
                  <button type="submit" disabled={loading}>Send</button>
                </form>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
                  {getButtons().map((label) => (
                    <button key={label} type="button" className="details-button" disabled={loading} onClick={() => continueConversation(label)}>{label}</button>
                  ))}
                  <button type="button" className="details-button" onClick={() => continueConversation("Cancel Request")} disabled={loading}>Cancel Request</button>
                </div>
              </>
            )}

            {showDetails && !submitted && (
              <form onSubmit={submitDetails} style={{ marginTop: 16, padding: 14, border: "1px solid #dfe5ec", borderRadius: 12 }}>
                <h3 style={{ marginTop: 0 }}>Support details</h3>
                <p style={{ fontSize: 13, marginTop: -4 }}>Share only details relevant to your issue. Never provide passwords or OTPs.</p>
                {(isPayment || isRefund) && <>
                  <label>Transaction / order ID</label><input value={details.transaction_id} onChange={(e) => setDetails({ ...details, transaction_id: e.target.value })} placeholder="Transaction or order ID" />
                  <label>Payment / purchase date</label><input type="date" value={details.date} onChange={(e) => setDetails({ ...details, date: e.target.value })} />
                  <label>Amount (₹)</label><input value={details.amount} onChange={(e) => setDetails({ ...details, amount: e.target.value })} placeholder="Amount" />
                </>}
                {isBatch && <><label>Batch name</label><input value={details.batch_name} onChange={(e) => setDetails({ ...details, batch_name: e.target.value })} placeholder="Your batch name" /></>}
                {isTechnical && <><label>Device / app or website</label><input value={details.device} onChange={(e) => setDetails({ ...details, device: e.target.value })} placeholder="e.g. Android app" /></>}
                <label>Registered email or phone</label><input value={details.registered_contact} onChange={(e) => setDetails({ ...details, registered_contact: e.target.value })} placeholder="Registered email or phone" />
                <label>Additional details</label><textarea rows={2} value={details.issue_details} onChange={(e) => setDetails({ ...details, issue_details: e.target.value })} placeholder="What happened? Any error message?" />
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
                  <button type="submit" disabled={loading}>{loading ? "Submitting..." : "Submit support request"}</button>
                  <button type="button" className="details-button" onClick={() => setShowDetails(false)} disabled={loading}>Back to chat</button>
                </div>
              </form>
            )}

            {submitted && <div style={{ marginTop: 14, fontSize: 14 }}><strong>Ticket #{submitted.ticket_id}</strong> · Saved to the support queue. This prototype does not send an external email or WhatsApp notification.</div>}
            {finished && <p style={{ marginTop: 14 }}>Glad I could help. Start a new chat whenever you need.</p>}
            {sources.length > 0 && <details style={{ marginTop: 14, fontSize: 13 }}><summary style={{ cursor: "pointer" }}>📚 Sources · {sources.length} document{sources.length === 1 ? "" : "s"}</summary><ul>{sources.map((source, index) => <li key={`${source}-${index}`}>{readableSource(source)}</li>)}</ul></details>}
          </section>
        )}

        {error && <div className="error" style={{ marginTop: 12 }}>{error}</div>}
        <footer><p>AI Support Ticket Triage Agent · Prototype</p><p>Support tickets are saved only when you submit the support form.</p></footer>
      </main>
    </div>
  );
}

// ================= SHARED COMPONENTS =================

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value || "N/A"}</strong>
    </div>
  );
}

function StatCard({ label, value, detail, symbol }) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <span>{label}</span>
        <span className="stat-symbol">{symbol}</span>
      </div>

      <strong>{value}</strong>

      <p>{detail}</p>
    </div>
  );
}

// ================= ADMIN DASHBOARD =================

function AdminDashboard() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedTicket, setSelectedTicket] = useState(null);

  // FRONTEND TESTING STATE

  const [sampleInput, setSampleInput] = useState(
    `I purchased a batch but it is not showing in my account.
I was charged twice for the same course.
I want a refund for my online batch.
The app crashes when I open my course.
Please help me solve this mathematics question.
I paid but my course access is still unavailable.
I am angry because nobody resolved my payment issue.
My books have not arrived and I cannot access my batch.
I purchased the wrong batch by mistake.
I need help with an issue I cannot explain properly.`
  );

  const [sampleResults, setSampleResults] = useState([]);
  const [sampleLoading, setSampleLoading] = useState(false);
  const [sampleError, setSampleError] = useState("");
  const [sampleSummary, setSampleSummary] = useState(null);

  // LOAD TICKETS

  async function loadTickets() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/tickets`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not load tickets.");
      }

      setTickets(data.tickets || []);
    } catch (err) {
      setError(
        err.message === "Failed to fetch"
          ? "Backend se connection nahi ho raha. FastAPI running hai?"
          : err.message
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTickets();
  }, []);

  // RUN SAMPLE TICKETS

  async function runSampleTests() {
    const inputTickets = sampleInput
      .split("\n")
      .map((line) =>
        line.replace(/^\s*\d+[.)]\s*/, "").trim()
      )
      .filter(Boolean);

    if (inputTickets.length !== 10) {
      setSampleError(
        `Exactly 10 tickets required. You entered ${inputTickets.length}.`
      );

      setSampleResults([]);
      setSampleSummary(null);
      return;
    }

    setSampleLoading(true);
    setSampleError("");
    setSampleResults([]);
    setSampleSummary(null);

    try {
      const response = await fetch(`${API_URL}/test-tickets`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          tickets: inputTickets,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Sample testing failed.");
      }

      setSampleResults(data.results || []);

      setSampleSummary({
        total: data.total_tested ?? inputTickets.length,
        successful: data.successful ?? 0,
        failed: data.failed ?? 0,
      });
    } catch (err) {
      setSampleError(
        err.message === "Failed to fetch"
          ? "Backend connection failed. Check whether FastAPI is running and the /test-tickets endpoint exists."
          : err.message
      );
    } finally {
      setSampleLoading(false);
    }
  }

  // DASHBOARD STATISTICS

  const humanReviewCount = tickets.filter(
    (ticket) => ticket.needs_human_review
  ).length;

  const highRiskCount = tickets.filter(
    (ticket) => ticket.risk_level?.toLowerCase() === "high"
  ).length;

  const autoReplyCount = tickets.filter(
    (ticket) => ticket.action === "AUTO_REPLY_CANDIDATE"
  ).length;

  const categories = [
    ...new Set(
      tickets.map((ticket) => ticket.category).filter(Boolean)
    ),
  ];

  // FILTER TICKETS

  const filteredTickets = tickets.filter((ticket) => {
    const searchText = search.toLowerCase();

    const matchesSearch =
      String(ticket.ticket_id).includes(searchText) ||
      (ticket.ticket || "").toLowerCase().includes(searchText) ||
      (ticket.reason || "").toLowerCase().includes(searchText);

    const matchesCategory =
      categoryFilter === "all" ||
      ticket.category === categoryFilter;

    const matchesRisk =
      riskFilter === "all" ||
      ticket.risk_level?.toLowerCase() === riskFilter;

    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "review" && ticket.needs_human_review) ||
      (statusFilter === "auto" &&
        ticket.action === "AUTO_REPLY_CANDIDATE");

    return (
      matchesSearch &&
      matchesCategory &&
      matchesRisk &&
      matchesStatus
    );
  });

  return (
    <div className="admin-page">
      {/* ADMIN HEADER */}

      <header className="header admin-header">
        <div className="logo">AI</div>

        <div>
          <h1>Support Operations</h1>
          <p>AI Support Ticket Triage · Admin Console</p>
        </div>

        <a className="admin-link" href="/">
          ← Student Interface
        </a>
      </header>

      <main className="admin-container">
        {/* DASHBOARD INTRO */}

        <section className="admin-welcome">
          <div>
            <span className="eyebrow">SUPPORT OVERVIEW</span>

            <h2>Ticket Dashboard</h2>

            <p>
              Monitor student queries, review AI decisions,
              and inspect drafted responses.
            </p>
          </div>

          <button
            onClick={loadTickets}
            disabled={loading}
          >
            {loading ? "Loading..." : "↻ Refresh Tickets"}
          </button>
        </section>

        {error && (
          <div className="error">
            {error}
          </div>
        )}

        {/* ADMIN STATISTICS */}

        <section className="admin-stats">
          <StatCard
            label="Total Tickets"
            value={tickets.length}
            detail="All recorded tickets"
            symbol="▤"
          />

          <StatCard
            label="Needs Human Review"
            value={humanReviewCount}
            detail="Requires support verification"
            symbol="◷"
          />

          <StatCard
            label="High Risk"
            value={highRiskCount}
            detail="Marked high risk by agent"
            symbol="⚠"
          />

          <StatCard
            label="Auto-Reply Candidates"
            value={autoReplyCount}
            detail="Eligible according to current rules"
            symbol="✓"
          />
        </section>

        {/* TEST 10 SAMPLE TICKETS */}

        <section className="admin-panel sample-test-panel">
          <div className="table-heading">
            <div>
              <h3>Test 10 Sample Tickets</h3>

              <p>
                Paste exactly 10 queries, one ticket per line.
                These tests use the separate test endpoint and
                should not create normal ticket records.
              </p>
            </div>
          </div>

          <div className="sample-test-content">
            <label htmlFor="sampleInput">
              Sample student queries
            </label>

            <textarea
              id="sampleInput"
              className="sample-textarea"
              rows={10}
              value={sampleInput}
              onChange={(e) => setSampleInput(e.target.value)}
              placeholder="Paste 10 tickets, one per line..."
            />

            <div className="sample-actions">
              <span>
                {
                  sampleInput
                    .split("\n")
                    .filter((line) => line.trim()).length
                }
                {" / 10 tickets"}
              </span>

              <button
                onClick={runSampleTests}
                disabled={sampleLoading}
              >
                {sampleLoading
                  ? "Testing tickets..."
                  : "Run Test →"}
              </button>
            </div>

            {sampleError && (
              <div className="error">
                {sampleError}
              </div>
            )}

            {sampleSummary && (
              <div className="sample-summary">
                <StatCard
                  label="Processed"
                  value={sampleSummary.total}
                  detail="Sample tickets submitted"
                  symbol="▤"
                />

                <StatCard
                  label="Successful"
                  value={sampleSummary.successful}
                  detail="Processed without errors"
                  symbol="✓"
                />

                <StatCard
                  label="Failed"
                  value={sampleSummary.failed}
                  detail="Processing errors"
                  symbol="!"
                />
              </div>
            )}
          </div>

          {/* SAMPLE TEST RESULTS */}

          {sampleResults.length > 0 && (
            <div className="table-scroll">
              <table className="ticket-table">
                <thead>
                  <tr>
                    <th>Test #</th>
                    <th>Student Query</th>
                    <th>Category</th>
                    <th>Sentiment</th>
                    <th>Risk</th>
                    <th>Priority</th>
                    <th>Action</th>
                    <th>Details</th>
                  </tr>
                </thead>

                <tbody>
                  {sampleResults.map((item) => (
                    <tr key={item.test_id}>
                      <td>#{item.test_id}</td>

                      <td className="query-cell">
                        {item.ticket}
                      </td>

                      <td>
                        {item.error
                          ? "Error"
                          : (item.category || "unknown").replaceAll(
                              "_",
                              " "
                            )}
                      </td>

                      <td>{item.sentiment || "—"}</td>

                      <td>
                        <span
                          className={`risk-pill ${(
                            item.risk_level || ""
                          ).toLowerCase()}`}
                        >
                          {item.risk_level || "—"}
                        </span>
                      </td>

                      <td>{item.priority || "—"}</td>

                      <td>
                        {item.error
                          ? "Failed"
                          : item.needs_human_review
                            ? "Human Review"
                            : item.action}
                      </td>

                      <td>
                        <button
                          className="details-button"
                          onClick={() =>
                            window.alert(
                              item.error
                                ? `Error: ${item.error}`
                                : `Ticket: ${item.ticket}\n\nCategory: ${item.category}\nSentiment: ${item.sentiment}\nRisk: ${item.risk_level}\nPriority: ${item.priority}\nAction: ${item.action}\n\nReason: ${item.reason}\n\nDraft reply:\n${item.draft_reply}\n\nSources: ${(item.sources || []).join(", ")}`
                            )
                          }
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* EXISTING TICKETS */}

        <section className="admin-panel">
          <div className="table-heading">
            <div>
              <h3>Support Tickets</h3>

              <p>
                {filteredTickets.length} tickets match your filters
              </p>
            </div>

            <input
              className="search-input"
              type="search"
              placeholder="Search ticket ID or query..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* FILTERS */}

          <div className="filters">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="all">All categories</option>

              {categories.map((category) => (
                <option key={category} value={category}>
                  {category.replaceAll("_", " ")}
                </option>
              ))}
            </select>

            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
            >
              <option value="all">All risk levels</option>
              <option value="low">Low risk</option>
              <option value="medium">Medium risk</option>
              <option value="high">High risk</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All statuses</option>
              <option value="review">Needs human review</option>
              <option value="auto">Auto-reply candidates</option>
            </select>
          </div>

          {/* TICKET TABLE */}

          {loading ? (
            <div className="empty-state">
              Loading tickets...
            </div>
          ) : filteredTickets.length === 0 ? (
            <div className="empty-state">
              No tickets match your filters.
            </div>
          ) : (
            <div className="table-scroll">
              <table className="ticket-table">
                <thead>
                  <tr>
                    <th>Ticket</th>
                    <th>Student Query</th>
                    <th>Category</th>
                    <th>Risk</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Details</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredTickets.map((ticket) => (
                    <tr key={ticket.ticket_id}>
                      <td className="ticket-id">
                        #{ticket.ticket_id}
                      </td>

                      <td className="query-cell">
                        {(ticket.ticket || "").length > 75
                          ? `${ticket.ticket.slice(0, 75)}...`
                          : ticket.ticket}
                      </td>

                      <td>
                        {(ticket.category || "unknown").replaceAll(
                          "_",
                          " "
                        )}
                      </td>

                      <td>
                        <span
                          className={`risk-pill ${(
                            ticket.risk_level || "low"
                          ).toLowerCase()}`}
                        >
                          {ticket.risk_level || "N/A"}
                        </span>
                      </td>

                      <td>{ticket.priority || "N/A"}</td>

                      <td>
                        <span
                          className={`status ${
                            ticket.needs_human_review
                              ? "review"
                              : "auto"
                          }`}
                        >
                          {ticket.needs_human_review
                            ? "Human Review"
                            : "Auto Candidate"}
                        </span>
                      </td>

                      <td>
                        <button
                          className="details-button"
                          onClick={() => setSelectedTicket(ticket)}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* SELECTED TICKET DETAILS */}

        {selectedTicket && (
          <section className="ticket-detail">
            <div className="detail-heading">
              <div>
                <span className="eyebrow">
                  TICKET DETAILS
                </span>

                <h2>
                  Ticket #{selectedTicket.ticket_id}
                </h2>
              </div>

              <button
                className="close-detail"
                onClick={() => setSelectedTicket(null)}
              >
                Close ×
              </button>
            </div>

            <div className="detail-grid">
              <Metric
                label="Category"
                value={selectedTicket.category}
              />

              <Metric
                label="Sentiment"
                value={selectedTicket.sentiment}
              />

              <Metric
                label="Risk Level"
                value={selectedTicket.risk_level}
              />

              <Metric
                label="Priority"
                value={selectedTicket.priority}
              />
            </div>

            <div className="detail-block">
              <h3>Student Query</h3>
              <p>{selectedTicket.ticket}</p>
            </div>

            <div className="detail-block">
              <h3>Routing Decision</h3>

              <p>
                <strong>Action:</strong>{" "}
                {selectedTicket.action}
              </p>

              <p>
                <strong>Human review:</strong>{" "}
                {selectedTicket.needs_human_review
                  ? "Required"
                  : "Not flagged"}
              </p>

              <p>
                <strong>Reason:</strong>{" "}
                {selectedTicket.reason}
              </p>
            </div>

            <div className="detail-block">
              <h3>AI-Drafted Reply</h3>

              <p className="reply-text">
                {selectedTicket.draft_reply}
              </p>

              <p className="disclaimer">
                Draft only. No message has been sent automatically.
              </p>
            </div>

            <div className="detail-block">
              <h3>Knowledge Base Sources</h3>

              {selectedTicket.sources?.length ? (
                <ul>
                  {selectedTicket.sources.map((source, index) => (
                    <li key={`${source}-${index}`}>
                      {source}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No sources recorded.</p>
              )}
            </div>

            <p className="detail-date">
              Created:{" "}
              {selectedTicket.created_at
                ? new Date(
                    selectedTicket.created_at
                  ).toLocaleString()
                : "Unknown"}
            </p>
          </section>
        )}

        {/* ADMIN FOOTER */}

        <footer>
          <p>
            AI Support Ticket Triage Agent · Admin Console
          </p>

          <p>
            Human-review decisions are recommendations.
            No replies are sent from this dashboard.
          </p>
        </footer>
      </main>
    </div>
  );
}

export default App;