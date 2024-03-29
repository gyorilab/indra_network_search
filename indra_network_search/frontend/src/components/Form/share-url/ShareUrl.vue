<template>
  <!-- Utilizes BootStrap 5's modal component -->
  <!-- Button triggering modal -->
  <span :title="isDisabled ? 'Must have results to be able to generate share link' : 'Click to get a shareable url'">
    <button
        type="button"
        :class="{ disabledButton: isDisabled }"
        class="btn btn-primary"
        :data-bs-toggle="isDisabled ? '' : 'modal'"
        :data-bs-target="isDisabled ? '' : `#${strUUID}`"
        :disabled="isDisabled"
    >
      <b>Share</b>
    </button>
  </span>

  <!-- Modal -->
  <div
    class="modal"
    :id="strUUID"
    tabindex="-1"
    :aria-labelledby="`label-${strUUID}`"
    aria-hidden="true"
  >
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" :id="`label-${strUUID}`">
            Share the result <span v-if="flashMessage" id="flashMessage">{{ flashMessage }}</span>
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>
        <div class="modal-body">
          <div class="input-group mb-3">
            <input
                type="text"
                class="form-control"
                placeholder="Search URL"
                :aria-describedby="copyBtnId"
                :value="shareUrl"
                readonly
            >
            <button
                class="btn btn-outline-secondary"
                type="button"
                @click="copyUrlToClipBoard()"
                :id="copyBtnId"
                :title="flashMessage"
            >Copy</button>
          </div>
        </div>
      </div>
    </div>
  </div>
  <!-- End modal -->
</template>

<script>
import UniqueID from "@/helpers/BasicHelpers";
import sharedHelpers from "@/helpers/sharedHelpers";

export default {
  name: "CopyUrl.vue",
  inject: ["GStore"],
  props: {
    nonFalseDefaults: {
      /** Object with defaults that are not equivalent to false
       *  - depth_limit_default: 2
       *  - k_shortest_default: 50
       *  - max_per_node_default: 5
       *  - const_tk_default: 10
       *  - const_c_default: 1
       *  - user_timeout_default: 30
       *  - weighted: "unweighted"
       * **/
      type: Object,
      required: true
    },
    isDisabled: {
      // Should be true when search has been done and a result exists for it,
      // including empty results
      type: Boolean,
      required: true
    }
  },
  methods: {
    isDefault(key, value) {
      // If key part of non-false defaults, check against default value
      if (key in this.nonFalseDefaults) {
        // NOTE: this might get more complicated if there are defaults
        // that are non-empty objects or arrays
        return this.nonFalseDefaults[key] === value
      }
      // Else just check if value evaluates to false
      return sharedHelpers.evaluatesToFalse(value)
    },
    getQueryString(queryObj) {
      let shareQuery = {}
      // Loop queryObj and check values are non-default
      for (const [key, value] of Object.entries(queryObj)) {
        if (key === 'format') {
          continue
        }
        // Save to new object if value is non-default
        if (!this.isDefault(key, value)) {
          shareQuery[key] = value
        }
      }
      const urlPars = new URLSearchParams(shareQuery)
      return urlPars.toString()
    },
    flashCopied() {
      this.flashMessage = 'Link copied!'
      setTimeout(() => {
        this.flashMessage = ''
      }, 3000)
    },
    copyUrlToClipBoard() {
      try {
        this.flashCopied() // Flashes the message
        navigator.clipboard.writeText(this.shareUrl)  // Copies the url
      } catch (e) {
        console.log('Could not copy Url to clipboard')
        throw e
      }
    }
  },
  data() {
    return {
      flashMessage: ''
    }
  },
  computed: {
    shareUrl() {
      /** Create URl with the parts:
       * BaseUrl: e.g. "https://network.indra.bio" or "http://localhost:8080"
       * Service Prefix: e.g. "/vue/"
       * query string: e.g. "?source=TNF&weighted=z_score"
       *
       * Return `${<BaseUrl>}${<Service Prefix>}${query string}`
      **/
      const origin = window.location.origin // Gets http(s)://hostname(:port)
      const path = window.location.pathname // Gets /location/
      const queryStr = this.getQueryString(this.GStore.currentQuery) // Generate from currentQuery
      const hash = window.location.href.includes('#') ? '#/' : ''
      let fullUrl = `${origin}${path}${hash}?${queryStr}`
      return fullUrl
    },
    strUUID() {
      return `modal-${this.uuid}`
    },
    copyBtnId() {
      return `copy-button-${this.uuid}`
    }
  },
  setup() {
    const uuid = UniqueID().getID();
    return {
      uuid,
    };
  },
}
</script>

<style scoped>
@keyframes yellowfade {
  from {
    color: black;
    background: yellow;
  }
  to {
    color: white;
    background: transparent;
  }
}

#flashMessage {
  animation-name: yellowfade;
  animation-duration: 3s;
}
</style>