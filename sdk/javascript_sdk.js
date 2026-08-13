// QB Protocol - JavaScript SDK
// Quick connect, no-login, geolocation matching, instance management.

class QBProtocolClient {
  constructor(baseUrl = "http://localhost:17760") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }
  async status() {
    const res = await fetch(`${this.baseUrl}/status`);
    return res.json();
  }
  async health() {
    const res = await fetch(`${this.baseUrl}/health`);
    return res.json();
  }
  async createInstance(name, platform = null, metadata = {}) {
    const res = await fetch(`${this.baseUrl}/instances`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({name, platform, metadata})
    });
    return res.json();
  }
  async startInstance(instanceId) {
    const res = await fetch(`${this.baseUrl}/instances/${instanceId}/start`, {method: "POST"});
    return res.json();
  }
  async stopInstance(instanceId) {
    const res = await fetch(`${this.baseUrl}/instances/${instanceId}/stop`, {method: "POST"});
    return res.json();
  }
  async registerCore(instanceId, coreType, threadId = null) {
    const res = await fetch(`${this.baseUrl}/cores`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({instance_id: instanceId, core_type: coreType, thread_id: threadId})
    });
    return res.json();
  }
  async coreHeartbeat(coreId, load = 0, temperature = 0) {
    const url = new URL(`${this.baseUrl}/cores/${coreId}/heartbeat`);
    url.searchParams.set("load", load);
    url.searchParams.set("temperature", temperature);
    const res = await fetch(url, {method: "POST"});
    return res.json();
  }
  async createDreamLayer(depth, projection, convergence = 0, brainStateEmission = 0, singularityThreshold = 0) {
    const res = await fetch(`${this.baseUrl}/dream/layers`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({depth, projection, convergence, brain_state_emission: brainStateEmission, singularity_threshold: singularityThreshold})
    });
    return res.json();
  }
  async dreamStatus() {
    const res = await fetch(`${this.baseUrl}/dream/status`);
    return res.json();
  }
  async stabilizerStatus() {
    const res = await fetch(`${this.baseUrl}/stabilizer/status`);
    return res.json();
  }
  async ipLookup(ip = null, provider = "ip-api") {
    const res = await fetch(`${this.baseUrl}/ip/lookup`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ip, provider})
    });
    return res.json();
  }
  async quickIP() {
    const res = await fetch(`${this.baseUrl}/ip/quick-connect`);
    return res.json();
  }
  async triggerRegen() {
    const res = await fetch(`${this.baseUrl}/healing/regen`, {method: "POST"});
    return res.json();
  }
  async healingStatus() {
    const res = await fetch(`${this.baseUrl}/healing/status`);
    return res.json();
  }
  async monitorIntegrate(mirrorUrl) {
    const url = new URL(`${this.baseUrl}/monitor/integrate`);
    url.searchParams.set("mirror_url", mirrorUrl);
    const res = await fetch(url, {method: "POST"});
    return res.json();
  }
}

module.exports = QBProtocolClient;
