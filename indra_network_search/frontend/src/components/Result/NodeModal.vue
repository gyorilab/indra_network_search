<template>
  <!-- Utilizes BootStrap 5's modal component -->
  <!-- Button triggered modal -->
  <a
    type="button"
    :title="title"
    @click="fillXrefs()"
    class="node-modal"
    data-bs-toggle="modal"
    :data-bs-target="`#${strUUID}`"
  >
    <b>{{ name }}</b>
  </a>

  <!-- Modal -->
  <div
    class="modal fade"
    :id="strUUID"
    tabindex="-1"
    :aria-labelledby="`label-${strUUID}`"
    aria-hidden="true"
  >
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" :id="`label-${strUUID}`">
            Cross References for {{ name }}
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>
        <div class="modal-body">
          <table class="table">
            <thead>
              <tr>
                <th>Namespace</th>
                <th>Identifier</th>
                <th>Lookup</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(triple, index) in allRefs"
                :key="`${strUUID}-row${index}`"
              >
                <td>{{ triple[0] }}</td>
                <td>{{ triple[1] }}</td>
                <td>
                  <a :href="triple[2]" target="_blank">
                    <i class="bi bi-box-arrow-up-right"></i>
                  </a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="modal-footer">
          <span v-show="serverError">The server has an error...</span><br />
          <button
            type="button"
            class="btn btn-secondary"
            data-bs-dismiss="modal"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AxiosMethods from "@/services/AxiosMethods";
import UniqueID from "@/helpers/BasicHelpers";

export default {
  inject: ["GStore"],
  // Match the fields of class Node in indra_network_search/data_models.py
  props: {
    name: {
      type: String,
      default: "",
    },
    namespace: {
      type: String,
      required: true,
    },
    identifier: {
      type: String,
      required: true,
    },
    sign: {
      // Currently unused in this context
      type: Number,
      default: null,
    },
    lookup: {
      type: String,
      default: "",
    },
  },
  data() {
    return {
      xrefs: [],
      serverError: false,
    };
  },
  computed: {
    title() {
      return (
        `Grounded to: ${this.namespace}:${this.identifier}. ` +
        "Click for more info"
      );
    },
    allRefs() {
      return [
        ...[[this.namespace, this.identifier, this.lookup]],
        ...this.xrefs,
      ];
    },
    strUUID() {
      return `modal-${this.uuid}`;
    },
  },
  methods: {
    fillXrefs() {
      if (this.GStore.xrefs[this.name]) {
        // Check for xrefs in GStore
        console.log("Found xref in GStore");
        this.xrefs = this.GStore.xrefs[this.name];
      } else if (!this.xrefs.length) {
        // Get xrefs from server
        AxiosMethods.getXrefs(this.namespace, this.identifier)
          .then((response) => {
            this.serverError = false;
            const xrefData = response.data;
            this.xrefs = xrefData;
            this.GStore.xrefs[this.name] = xrefData;
            console.log("Got xrefs from server");
          })
          .catch((error) => {
            console.log(error);
            this.serverError = true;
          });
      } else {
        // Nothing needs to be done
        return false;
      }
    },
  },
  setup() {
    const uuid = UniqueID().getID();
    return {
      uuid,
    };
  },
};
</script>
