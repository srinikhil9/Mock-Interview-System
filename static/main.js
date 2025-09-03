document.addEventListener("DOMContentLoaded", () => {
	const API_BASE = "http://127.0.0.1:8000";
	let sessionId = null;
	let sessionData = {};

	const newSessionBtn = document.getElementById("new-session-btn");
	const sessionList = document.getElementById("session-list");
	const chatMessages = document.getElementById("chat-messages");
	const messageInput = document.getElementById("message-input");
	const sendBtn = document.getElementById("send-btn");
	const resumeUpload = document.getElementById("resume-upload");
	const jdUpload = document.getElementById("jd-upload");
	const resumeFileName = document.getElementById("resume-file-name");
	const jdFileName = document.getElementById("jd-file-name");

	async function post(path, body) {
		const response = await fetch(`${API_BASE}${path}`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body),
		});
		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.detail || "An error occurred");
		}
		return response.json();
	}

	function addMessage(sender, text) {
		const messageElement = document.createElement("div");
		messageElement.classList.add("message");
		messageElement.innerHTML = `<p class="sender">${sender}</p><p>${text}</p>`;
		chatMessages.appendChild(messageElement);
		chatMessages.scrollTop = chatMessages.scrollHeight;
	}

	function displayWelcomeMessage() {
		addMessage(
			"System",
			"Welcome to your technical interview. Please upload your resume and the job description, then send a message to begin. You can type '/next' to switch topics or '/quit' to end the session at any time."
		);
	}

	async function createNewSession() {
		try {
			const resumeFile = resumeUpload.files[0];
			const jdFile = jdUpload.files[0];

			if (!resumeFile || !jdFile) {
				addMessage("System", "Please upload both a resume and a job description.");
				return;
			}
   const formData = new FormData();
   formData.append("resume", resumeFile);
   formData.append("jd", jdFile);
   
			const response = await fetch(`${API_BASE}/api/session`, {
    method: "POST",
    body: formData,
   });

   if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "An error occurred");
   }
   const session = await response.json();

			sessionId = session.session_id;
			sessionData[sessionId] = {
				candidate: session.candidate_name,
				role: session.target_role,
				messages: [],
			};

			addMessage(
				"System",
				`Session started for ${session.candidate_name} (Role: ${session.target_role}). Topics: ${session.topics.join(", ")}.`
			);
			updateSessionList();
			await nextQuestion();
		} catch (error) {
			addMessage("System", `Error: ${error.message}`);
		}
	}

	async function nextQuestion() {
		if (!sessionId) return;
		try {
			const response = await post("/api/next", { session_id: sessionId });
			addMessage(
				`Interviewer (Topic: ${response.topic})`,
				response.question
			);
		} catch (error) {
			addMessage("System", `Error: ${error.message}`);
		}
	}

	async function handleSendMessage() {
		if (!sessionId) {
			await createNewSession();
			messageInput.value = "";
			return;
		}

		const answer = messageInput.value.trim();
		if (!answer || !sessionId) return;

		addMessage("You", answer);
		messageInput.value = "";

		try {
			const response = await post("/api/answer", {
				session_id: sessionId,
				answer: answer,
			});

			let feedback = `Feedback: ${response.brief_feedback} (Score: ${response.score.toFixed(1)}/10)`;
			if (response.strengths.length > 0) {
				feedback += `\nStrengths: ${response.strengths.join(", ")}`;
			}
			if (response.improvements.length > 0) {
				feedback += `\nAreas for Improvement: ${response.improvements.join(", ")}`;
			}
			addMessage("Evaluator", feedback);

			if (response.hint) {
				addMessage("Hint", response.hint);
			}

			if (response.follow_up_question) {
				addMessage("Interviewer", response.follow_up_question);
			} else {
				await nextQuestion();
			}
		} catch (error) {
			addMessage("System", `Error: ${error.message}`);
		}
	}

	function updateSessionList() {
		sessionList.innerHTML = "";
		for (const id in sessionData) {
			const session = sessionData[id];
			const sessionElement = document.createElement("div");
			sessionElement.classList.add("session-item");
			sessionElement.textContent = `${session.candidate} - ${session.role}`;
			sessionElement.dataset.sessionId = id;
			sessionList.appendChild(sessionElement);
		}
	}

	newSessionBtn.addEventListener("click", createNewSession);
	sendBtn.addEventListener("click", handleSendMessage);
	messageInput.addEventListener("keydown", (e) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			handleSendMessage();
		}
	});

	resumeUpload.addEventListener("change", () => {
		resumeFileName.textContent = resumeUpload.files[0]
			? resumeUpload.files[0].name
			: "Resume";
	});

	jdUpload.addEventListener("change", () => {
		jdFileName.textContent = jdUpload.files[0]
			? jdUpload.files[0].name
			: "Job Description";
	});

	displayWelcomeMessage();
});
