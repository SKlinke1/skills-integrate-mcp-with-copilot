document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const userMenuButton = document.getElementById("user-menu-button");
  const userMenu = document.getElementById("user-menu");
  const loginButton = document.getElementById("login-button");
  const logoutButton = document.getElementById("logout-button");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginError = document.getElementById("login-error");
  let isTeacher = false;
  let messageTimeout;

  function showMessage(message, type) {
    messageDiv.textContent = message;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
    clearTimeout(messageTimeout);
    messageTimeout = setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  async function refreshAuthState() {
    const response = await fetch("/auth/session");
    if (!response.ok) {
      throw new Error("Unable to check teacher login status.");
    }

    const session = await response.json();
    isTeacher = session.authenticated;
    loginButton.hidden = isTeacher;
    logoutButton.hidden = !isTeacher;
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error("Unable to load activities.");
      }
      const activities = await response.json();

      activitiesList.replaceChildren();
      while (activitySelect.options.length > 1) {
        activitySelect.remove(1);
      }

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const heading = document.createElement("h4");
        heading.textContent = name;
        activityCard.appendChild(heading);

        const description = document.createElement("p");
        description.textContent = details.description;
        activityCard.appendChild(description);

        const schedule = document.createElement("p");
        const scheduleLabel = document.createElement("strong");
        scheduleLabel.textContent = "Schedule: ";
        schedule.append(scheduleLabel, document.createTextNode(details.schedule));
        activityCard.appendChild(schedule);

        const spotsLeft = document.createElement("p");
        const availabilityLabel = document.createElement("strong");
        availabilityLabel.textContent = "Availability: ";
        spotsLeft.append(
          availabilityLabel,
          document.createTextNode(
            `${details.max_participants - details.participants.length} spots left`
          )
        );
        activityCard.appendChild(spotsLeft);

        const participantsContainer = document.createElement("div");
        participantsContainer.className = "participants-container";
        const participantsSection = document.createElement("div");
        participantsSection.className = "participants-section";

        if (details.participants.length > 0) {
          const participantsHeading = document.createElement("h5");
          participantsHeading.textContent = "Participants:";
          participantsSection.appendChild(participantsHeading);

          const participantsList = document.createElement("ul");
          participantsList.className = "participants-list";
          details.participants.forEach((email) => {
            const participant = document.createElement("li");
            const emailLabel = document.createElement("span");
            emailLabel.className = "participant-email";
            emailLabel.textContent = email;
            participant.appendChild(emailLabel);

            if (isTeacher) {
              const removeButton = document.createElement("button");
              removeButton.type = "button";
              removeButton.className = "delete-btn";
              removeButton.dataset.activity = name;
              removeButton.dataset.email = email;
              removeButton.setAttribute(
                "aria-label",
                `Unregister ${email} from ${name}`
              );
              removeButton.textContent = "Remove";
              removeButton.addEventListener("click", handleUnregister);
              participant.appendChild(removeButton);
            }

            participantsList.appendChild(participant);
          });
          participantsSection.appendChild(participantsList);
        } else {
          const emptyMessage = document.createElement("p");
          emptyMessage.textContent = "No participants yet";
          participantsSection.appendChild(emptyMessage);
        }

        participantsContainer.appendChild(participantsSection);
        activityCard.appendChild(participantsContainer);
        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
    } catch (error) {
      activitiesList.textContent =
        "Failed to load activities. Please try again later.";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = button.dataset.activity;
    const email = button.dataset.email;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "An error occurred");
      }

      showMessage(result.message, "success");
      await fetchActivities();
    } catch (error) {
      showMessage(
        error.message || "Failed to unregister. Please try again.",
        "error"
      );
      console.error("Error unregistering:", error);
    }
  }

  userMenuButton.addEventListener("click", () => {
    const isExpanded = userMenuButton.getAttribute("aria-expanded") === "true";
    userMenuButton.setAttribute("aria-expanded", String(!isExpanded));
    userMenu.classList.toggle("hidden", isExpanded);
  });

  loginButton.addEventListener("click", () => {
    userMenu.classList.add("hidden");
    userMenuButton.setAttribute("aria-expanded", "false");
    loginError.textContent = "";
    loginError.classList.add("hidden");
    loginDialog.showModal();
  });

  document.getElementById("cancel-login").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.classList.add("hidden");

    const credentials = {
      username: document.getElementById("username").value,
      password: document.getElementById("password").value,
    };

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Unable to log in.");
      }

      loginDialog.close();
      loginForm.reset();
      await refreshAuthState();
      await fetchActivities();
      showMessage("Teacher logged in.", "success");
    } catch (error) {
      loginError.textContent = error.message || "Unable to log in.";
      loginError.classList.remove("hidden");
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error("Unable to log out.");
      }
      await refreshAuthState();
      await fetchActivities();
      userMenu.classList.add("hidden");
      userMenuButton.setAttribute("aria-expanded", "false");
      showMessage("Teacher logged out.", "success");
    } catch (error) {
      showMessage(error.message || "Unable to log out.", "error");
    }
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = activitySelect.value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        { method: "POST" }
      );
      const result = await response.json();

      if (!response.ok) {
        if (response.status === 401) {
          isTeacher = false;
          await refreshAuthState();
          await fetchActivities();
        }
        throw new Error(result.detail || "An error occurred");
      }

      showMessage(result.message, "success");
      signupForm.reset();
      await fetchActivities();
    } catch (error) {
      showMessage(
        error.message || "Failed to register student. Please try again.",
        "error"
      );
      console.error("Error registering student:", error);
    }
  });

  refreshAuthState()
    .catch((error) => {
      console.error("Error checking teacher login status:", error);
    })
    .finally(fetchActivities);
});
