import axios from "axios";

const baseUrl = "https://network.indra.bio/dev";

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
    return apiGetClient.get(`/nodes_in_graph?prefix=${prefix}`)
  }
};
