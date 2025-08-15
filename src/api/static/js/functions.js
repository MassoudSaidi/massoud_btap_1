async function fetchProtectedData_old() {
  try {
    const res = await fetch("/api/v1/data", {
      method: "GET",
      credentials: "include" // Required for cookies
    });

    if (res.status === 200) {
      const data = await res.json();
      console.log("Protected data:", data);
      alert("Data: " + JSON.stringify(data, null, 2));
    } else if (res.status === 401) {
      console.log("Not authenticated. Redirecting to login...");
    } else {
      console.error("Unexpected error", res.status);
      alert("An error occurred: " + res.status);
    }
  } catch (err) {
    console.error("Fetch error:", err);
    alert("Network or server error");
  }
}

async function fetchProtectedData() {
  try {
    console.log("fetchProtectedData");
    const res = await fetch("/api/v1/data", {
      method: "GET",
      credentials: "include"
    });

    const container = document.getElementById("api-response");
    console.log(res);

    if (res.status === 200) {
      const data = await res.json();
      console.log("Protected data:", data);

      container.textContent = JSON.stringify(data, null, 2);
      container.classList.remove("hidden");
    } else if (res.status === 401) {
      //window.location.href = window.cognitoLoginUrl;
      container.textContent = "Authentication Error: " + res.status;
      container.classList.remove("hidden");      
    } else {
      container.textContent = "Unexpected error2: " + res.status;
      container.classList.remove("hidden");
    }
  } catch (err) {
    console.error("Fetch error:", err);
    const container = document.getElementById("api-response");
    container.textContent = "Network or server error.";
    container.classList.remove("hidden");
  }
}
