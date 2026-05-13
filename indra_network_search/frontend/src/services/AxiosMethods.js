import axios from "axios";

const baseUrl = "https://network.indra.bio/api";

const apiClient = axios.create({
  baseURL: baseUrl,
  withCredentials: false,
  headers: {
    Accept: "application/json",
    "Content-Type": "application/json",
  },
});

const apiGetClient = axios.create({
  baseURL: baseUrl,
  withCredentials: false,
});

export default {
  submitForm(networkSearchQuery) {
    return apiClient.post("/query", networkSearchQuery);
  },
  getXrefs(ns, id) {
    return apiGetClient.get(`/xrefs?ns=${ns}&id=${id}`);
  },
  auto(prefix) {
    return apiGetClient.get(`/autocomplete?prefix=${prefix}`);
  },
  autocompleteMesh(prefix) {
    return apiGetClient.get("/autocomplete-mesh-name", {
      params: { prefix },
    });
  },
  checkNode(name) {
    return apiGetClient.get(`/node-name-in-graph?node-name=${name}`);
  },
  checkNodeNSID(dbName, dbID) {
    return apiGetClient.get(
      `/node-name-in-graph?db-name=${dbName}&db-id=${dbID}`
    );
  },
  checkServerStatus() {
    return apiGetClient("/status");
  },
};
