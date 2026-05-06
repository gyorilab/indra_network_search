<template>
  <div class="container">
    <!--
      Todo:
        - Add hover or "?" text for help
        - See if it's possible to set form inputs to their defaults if the
          field/input is disabled. This could be done by checking
          $attrs.disabled, which will be Boolean if defined, otherwise
          undefined. Otherwise, check out vuelidate (until vuetify exists)
     -->
    <form id="search-form" @submit.prevent="sendForm">
      <h2 class="text-center">Basic Search Options</h2>
      <div class="container">
        <div class="row">
          <div class="col">
            <BaseInputAutoCompBS
              v-model="source"
              v-model:valid-node="validSource"
              label="Source node, e.g. 'MEK' or 'fplx:mek'"
              type="text"
              placeholder="e.g. 'MEK'"
              :allowWhitespace="false"
              :errors="v$.source.$errors"
              @blur="v$.source.$touch()"
              ref="sourceComponent"
            />
          </div>
          <div class="col">
            <BaseInputAutoCompBS
              v-model="target"
              v-model:valid-node="validTarget"
              label="Target node, e.g. 'ACE2' or 'hgnc:13557'"
              type="text"
              placeholder="e.g. 'ACE2'"
              :allowWhitespace="false"
              :errors="v$.target.$errors"
              @blur="v$.target.$touch()"
              ref="targetComponent"
            />
          </div>
        </div>
      </div>
      <h2 class="text-center">Detailed Search Options</h2>
      <div class="accordion" :id="accordionID">
        <!-- Accordion 1: General Filter Options -->
        <div class="accordion-item">
          <h3 class="accordion-header" :id="accordionIDObj.accordionHeader1ID">
            <button
              class="accordion-button collapsed"
              type="button"
              data-bs-toggle="collapse"
              :data-bs-target="`#${accordionIDObj.accordionBody1ID}`"
              aria-expanded="false"
              :aria-controls="accordionIDObj.accordionBody1ID"
            >
              <strong>General Options</strong>
              <template v-if="generalErrors"
                >|
                <span class="form-error">
                  {{ generalErrors }} error{{ generalErrors > 1 ? "s" : "" }}
                  detected
                </span>
              </template>
            </button>
          </h3>
          <div
            :id="accordionIDObj.accordionBody1ID"
            class="accordion-collapse collapse"
            :aria-labelledby="accordionIDObj.accordionHeader1ID"
          >
            <div class="accordion-body">
              <div class="container">
                <div class="row">
                  <div class="col">
                    <BaseInputBS
                      v-model.number="path_length"
                      :disabled="isAnyWeighted"
                      :max="10"
                      :min="1"
                      label="Path length"
                      type="number"
                      :errors="v$.path_length.$errors"
                      @blur="v$.path_length.$touch()"
                    />
                  </div>
                  <div class="col">
                    <BaseInputBS
                      v-model="node_blacklist_text"
                      label="Node Blacklist"
                      type="text"
                      :allowWhitespace="false"
                    />
                  </div>
                </div>
                <div class="row">
                  <div class="col">
                    <BaseInputBS
                      v-model.number="k_shortest"
                      :max="50"
                      :min="1"
                      label="Max Paths"
                      type="number"
                      :errors="v$.k_shortest.$errors"
                      @blur="v$.k_shortest.$touch()"
                    />
                  </div>
                  <div class="col">
                    <BaseSelectBS
                      v-model.number="sign"
                      :options="signOptions"
                      label="Signed Search"
                    />
                  </div>
                </div>
                <div class="row">
                  <div class="col">
                    <BaseInputBS
                      v-model.number="cull_best_node"
                      :min="1"
                      label="Highest Degree Node Culling Frequency"
                      :title="cullTitle"
                      type="number"
                      :errors="v$.cull_best_node.$errors"
                      @blur="v$.cull_best_node.$touch()"
                    />
                  </div>
                  <div class="col">
                    <BaseInputBS
                      v-model.number="belief_cutoff"
                      :max="1.0"
                      :min="0.0"
                      :step="0.01"
                      label="Belief Cutoff"
                      type="number"
                      :errors="v$.belief_cutoff.$errors"
                      @blur="v$.belief_cutoff.$touch()"
                    />
                  </div>
                </div>
                <div class="row">
                  <div class="col">
                    <Multiselect
                      v-model="stmt_filter"
                      mode="tags"
                      placeholder="Allowed Statement Types"
                      title="All types are allowed if no types are selected"
                      :searchable="true"
                      :createTag="false"
                      :options="stmtFilterOptions"
                    />
                  </div>
                  <div class="col">
                    <Multiselect
                      v-model="allowed_ns"
                      mode="tags"
                      placeholder="Allowed Node Namespaces"
                      title="All namespaces are allowed if no namespaces are selected"
                      :searchable="true"
                      :createTag="false"
                      :options="nodeNamespaceOptions"
                    />
                  </div>
                </div>
                <div class="row">
                  <div class="col-6">
                    <BaseCheckboxBS
                      v-model="curated_db_only"
                      label="Only Database Supported Sources"
                    />
                    <BaseCheckboxBS
                      v-model="fplx_edges"
                      label="Allow ontological edges"
                    />
                    <BaseCheckboxBS
                      v-model="two_way"
                      label="Include Reverse Search"
                    />
                    <BaseCheckboxBS
                      v-model="shared_regulators"
                      :disabled="!isNotOpenSearch && !cannotSubmit"
                      label="Include Search for shared regulators of source/target"
                    />
                  </div>
                  <div class="col-6"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- Accordion 2: Weighted and Context Search Options -->
        <div class="accordion-item">
          <h3 class="accordion-header" :id="accordionIDObj.accordionHeader2ID">
            <button
              class="accordion-button collapsed"
              type="button"
              data-bs-toggle="collapse"
              :data-bs-target="`#${accordionIDObj.accordionBody2ID}`"
              aria-expanded="false"
              :aria-controls="accordionIDObj.accordionBody2ID"
            >
              <strong>Context and Weighted Search Options</strong>
              <template v-if="contextErrors"
                >|
                <span class="form-error">
                  {{ contextErrors }} error{{ contextErrors > 1 ? "s" : "" }}
                  detected
                </span>
              </template>
            </button>
          </h3>
          <div
            :id="accordionIDObj.accordionBody2ID"
            class="accordion-collapse collapse"
            :aria-labelledby="accordionIDObj.accordionHeader2ID"
          >
            <div class="accordion-body">
              <div class="row">
                <div class="col-4">
                  <BaseSelectBS
                    v-model="weighted"
                    :options="weightOptions"
                    label="Weighted Search"
                  />
                </div>
                <div class="col-4">
                  <BaseInputBS
                    v-model="mesh_ids_text"
                    :disabled="weighted !== 'context'"
                    label="Mesh IDs (comma separated)"
                    type="text"
                    :allowWhitespace="false"
                    :errors="meshIdsFieldErrors"
                    @blur="touchMeshIds"
                  />
                </div>
                <div class="col-4">
                  <BaseInputBS
                    v-model.number="const_c"
                    :disabled="
                      weighted !== 'context' || strict_mesh_id_filtering
                    "
                    :max="100"
                    :min="1"
                    label="Constant C"
                    type="number"
                    :errors="v$.const_c.$errors"
                    @blur="v$.const_c.$touch()"
                  />
                </div>
              </div>
              <div class="row justify-content-end">
                <div class="col-4">
                  <BaseCheckboxBS
                    v-model="strict_mesh_id_filtering"
                    :disabled="weighted !== 'context'"
                    label="Strict Mesh ID filtering without weights"
                    title="Do an unweighted search that is restricted to the edges associated with the given mesh-ids"
                  />
                </div>
                <div class="col-4">
                  <BaseInputBS
                    v-model.number="const_tk"
                    :disabled="
                      weighted !== 'context' || strict_mesh_id_filtering
                    "
                    :max="100"
                    :min="1"
                    label="Constant Tk"
                    type="number"
                    :errors="v$.const_tk.$errors"
                    @blur="v$.const_tk.$touch()"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- Accordion 3: Open Search Options -->
        <div class="accordion-item">
          <h3 class="accordion-header" :id="accordionIDObj.accordionHeader3ID">
            <button
              class="accordion-button collapsed"
              type="button"
              data-bs-toggle="collapse"
              :data-bs-target="`#${accordionIDObj.accordionBody3ID}`"
              aria-expanded="false"
              :aria-controls="accordionIDObj.accordionBody3ID"
            >
              <strong>Open Search Options</strong>
              <template v-if="openErrors"
                >|
                <span class="form-error">
                  {{ openErrors }} error{{ openErrors > 1 ? "s" : "" }}
                  detected
                </span>
              </template>
            </button>
          </h3>
          <div
            :id="accordionIDObj.accordionBody3ID"
            class="accordion-collapse collapse"
            :aria-labelledby="accordionIDObj.accordionHeader3ID"
          >
            <div class="accordion-body">
              <!-- Disable open search options if both source and target are set -->
              <div class="container">
                <div class="row">
                  <div class="col">
                    <!-- Check: is terminal ns applied for strict Dijkstra and/or context search? -->
                    <Multiselect
                      v-model="terminal_ns"
                      mode="tags"
                      placeholder="Terminal Namespaces"
                      title="Select the namespaces for which open searches must end on"
                      :disabled="isContextSearch || isNotOpenSearch"
                      :searchable="true"
                      :createTag="false"
                      :options="nodeNamespaceOptions"
                    />
                  </div>
                  <div class="col">
                    <!-- Disable max per node if weighted or context search -->
                    <BaseInputBS
                      v-model="max_per_node"
                      :disabled="
                        isNotOpenSearch || isContextSearch || isAnyWeighted
                      "
                      :min="1"
                      label="Max children per node"
                      type="number"
                      :errors="v$.max_per_node.$errors"
                      @blur="v$.max_per_node.$touch()"
                    />
                    <BaseInputBS
                      v-model="depth_limit"
                      :disabled="
                        isNotOpenSearch || isContextSearch || isAnyWeighted
                      "
                      :min="1"
                      label="Depth limit in unweighted search"
                      type="number"
                      :errors="v$.depth_limit.$errors"
                      @blur="v$.depth_limit.$touch()"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- end accordion -->
      <div
        class="row justify-content-center align-middle d-flex align-items-center"
        style="margin-top: 10px"
      >
        <div class="col-4">
          <p v-if="fillFormError" class="form-error">Failed to fill out some form values, check url query</p>
        </div>
        <div class="col-2">
          <button
            :class="{ disabledButton: cannotSubmit }"
            :disabled="cannotSubmit || isLoading || v$.$invalid"
            class="button btn btn-secondary btn-lg"
            type="submit"
          >
            <template v-if="isLoading">
              <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
            </template>
            Submit
          </button>
        </div>
        <div class="col-2 text-center">
          <BaseInputBS
            v-model.number="user_timeout"
            :max="120"
            :min="2"
            :step="1"
            :style="{ maxWidth: '100px' }"
            label="Timeout"
            type="number"
            :errors="v$.user_timeout.$errors"
            @blur="v$.user_timeout.$touch()"
          />
        </div>
        <div class="col-4">
          <ShareUrl
              :nonFalseDefaults="nonFalseDefaultValues"
              :isDisabled="emptyResult"
          />
        </div>
      </div>
    </form>
  </div>
  <RequestError v-if="submissionError" :axios-error="submissionError" />
  <ResultArea v-if="!emptyResult" v-bind="results" />
  <template v-else-if="!isLoading && emptyResult">
    <i>No results</i>
  </template>
</template>

<script>
import BaseSelectBS from "@/components/Form/BaseSelectBS";
import BaseCheckboxBS from "@/components/Form/BaseCheckboxBS";
import BaseInputBS from "@/components/Form/BaseInputBS";
import BaseInputAutoCompBS from "@/components/Form/BaseInputAutoCompBS";
import ShareUrl from "@/components/Form/share-url/ShareUrl";
import AxiosMethods from "@/services/AxiosMethods";
import UniqueID from "@/helpers/BasicHelpers";
import ResultArea from "@/components/Result/result_area/ResultArea";
import RequestError from "@/components/request_error/RequestError";
import Multiselect from "@vueform/multiselect";
import sharedHelpers from "@/helpers/sharedHelpers";
import DefaultValues from "../../public/DefaultValues"
import useVuelidate from "@vuelidate/core";
import {between, helpers, minLength, minValue, requiredIf,} from "@vuelidate/validators";

const cullFreq = (val) => !helpers.req(val) || val > 0;

export default {
  inject: ["GStore"],
  components: {
    RequestError,
    BaseInputAutoCompBS,
    ResultArea,
    BaseSelectBS,
    BaseCheckboxBS,
    BaseInputBS,
    Multiselect,
    ShareUrl,
  },
  data() {
    return {
      querySearchExec: false, // flag for if form is filled from url query
      validSource: false,
      validTarget: false,
      /* Begin query */
      source: "",
      target: "",
      stmt_filter: [],
      filter_curated: true,
      allowed_ns: [],
      node_blacklist_text: "",
      path_length: null,
      depth_limit: DefaultValues.DEPTH_LIMIT,
      sign: null,
      weighted: DefaultValues.WEIGHTED,
      belief_cutoff: 0.0,
      curated_db_only: false,
      fplx_expand: false,
      fplx_edges: false,
      k_shortest: DefaultValues.K_SHORTEST,
      max_per_node: DefaultValues.MAX_PER_NODE,
      cull_best_node: null,
      mesh_ids_text: "",
      meshIdsTouched: false,
      strict_mesh_id_filtering: false,
      const_c: DefaultValues.CONST_C,
      const_tk: DefaultValues.CONST_TK,
      user_timeout: DefaultValues.USER_TIMEOUT,
      two_way: false,
      shared_regulators: false,
      terminal_ns: [],
      format: "html", // This is hardcoded here and is not an option
      /* End query */
      cullTitle:
        "At the specified frequency, the highest degree node will " +
        "be added to the node blacklist and excluded from further " +
        "results for path queries (only applies to breadth first search " +
        "and source-target path searches)",
      isLoading: false,
      nonFalseDefaultValues: {
        depth_limit: DefaultValues.DEPTH_LIMIT,
        k_shortest: DefaultValues.K_SHORTEST,
        max_per_node: DefaultValues.MAX_PER_NODE,
        const_c: DefaultValues.CONST_C,
        const_tk: DefaultValues.CONST_TK,
        user_timeout: DefaultValues.USER_TIMEOUT,
        weighted: DefaultValues.WEIGHTED,
      },
      signOptions: [
        { label: "+", value: 0 },
        { label: "-", value: 1 },
        { label: "No sign", value: null },
      ],
      weightOptions: [
        { label: "Belief weighted", value: "belief" },
        { label: "DepMap z-score weighted", value: "z_score" },
        { label: "Mesh Context", value: "context" },
        { label: "Unweighted", value: "unweighted" },
      ],
      stmtFilterOptions: [
        // Idea:Load options from an endpoint that returns all options,
        // perhaps static served via "/data" or on S3? This allows a
        // basemodel to be used
        { label: "Gef", value: "Gef" },
        { label: "Gap", value: "Gap" },
        { label: "Complex", value: "Complex" },
        { label: "Translocation", value: "Translocation" },
        { label: "RegulateAmount", value: "RegulateAmount" },
        { label: "Conversion", value: "Conversion" },
        { label: "AddModification", value: "AddModification" },
        { label: "RemoveModification", value: "RemoveModification" },
        { label: "Phosphorylation", value: "Phosphorylation" },
        { label: "Hydroxylation", value: "Hydroxylation" },
        { label: "Sumoylation", value: "Sumoylation" },
        { label: "Acetylation", value: "Acetylation" },
        { label: "Glycosylation", value: "Glycosylation" },
        { label: "Ribosylation", value: "Ribosylation" },
        { label: "Ubiquitination", value: "Ubiquitination" },
        { label: "Farnesylation", value: "Farnesylation" },
        { label: "Geranylgeranylation", value: "Geranylgeranylation" },
        { label: "Palmitoylation", value: "Palmitoylation" },
        { label: "Myristoylation", value: "Myristoylation" },
        { label: "Methylation", value: "Methylation" },
        { label: "Dephosphorylation", value: "Dephosphorylation" },
        { label: "Dehydroxylation", value: "Dehydroxylation" },
        { label: "Desumoylation", value: "Desumoylation" },
        { label: "Deacetylation", value: "Deacetylation" },
        { label: "Deglycosylation", value: "Deglycosylation" },
        { label: "Deribosylation", value: "Deribosylation" },
        { label: "Deubiquitination", value: "Deubiquitination" },
        { label: "Defarnesylation", value: "Defarnesylation" },
        { label: "Degeranylgeranylation", value: "Degeranylgeranylation" },
        { label: "Depalmitoylation", value: "Depalmitoylation" },
        { label: "Demyristoylation", value: "Demyristoylation" },
        { label: "Demethylation", value: "Demethylation" },
        { label: "Autophosphorylation", value: "Autophosphorylation" },
        { label: "Transphosphorylation", value: "Transphosphorylation" },
        { label: "Inhibition", value: "Inhibition" },
        { label: "Activation", value: "Activation" },
        { label: "GtpActivation", value: "GtpActivation" },
        { label: "Association", value: "Association" },
        { label: "DecreaseAmount", value: "DecreaseAmount" },
        { label: "IncreaseAmount", value: "IncreaseAmount" },
      ],
      nodeNamespaceOptions: [
        { label: "FPLX (Genes/Proteins)", value: "fplx" },
        { label: "UPPRO (Protein Chains)", value: "uppro" },
        { label: "HGNC (Genes/Proteins)", value: "hgnc" },
        { label: "UP (Genes/Proteins)", value: "up" },
        { label: "CHEBI (Small Molecules)", value: "chebi" },
        { label: "GO (Biological Process or Location)", value: "go" },
        { label: "MESH (Biological Process or Disease)", value: "mesh" },
        { label: "MIRBASE (microRNA)", value: "mirbase" },
        { label: "DOID (Diseases)", value: "doid" },
        { label: "HP (Phenotypic Abnormality)", value: "hp" },
        { label: "EFO (Experimental factors)", value: "efo" },
      ],
      results: DefaultValues.EMPTY_RESULTS,
      submissionError: null,
      fillFormError: false, // Maybe make it an Array and store all errors
    };
  },
  computed: {
    // putting networkSearchQuery as a computed property makes it
    // automatically update whenever any of the dependencies (i.e. all the
    // options) update. This allows to use the component methods like
    // this.splitTrim() to make an array of comma separated text.
    // This object should conform with
    // indra_network_search.data_model.NetworkSearchQuery
    networkSearchQuery() {
      return {
        source: this.source,
        target: this.target,
        stmt_filter: this.fplx_edges ? [...this.stmt_filter, 'fplx'] : this.stmt_filter, // Multiselect; add fplx edges
        filter_curated: this.filter_curated,
        allowed_ns: this.allowed_ns, // Pick from multi-select
        node_blacklist: this.splitTrim(this.node_blacklist_text),
        path_length:
          this.path_length === "" ||
          this.path_length == null ||
          (typeof this.path_length === "number" && Number.isNaN(this.path_length)) ||
          this.path_length === 0
            ? null
            : this.path_length,
        depth_limit: this.depth_limit,
        sign: this.sign === "" ? null : this.sign,
        weighted: this.weighted,
        belief_cutoff: this.belief_cutoff,
        curated_db_only: this.curated_db_only,
        fplx_expand: this.fplx_expand,
        k_shortest: this.k_shortest,
        max_per_node: this.max_per_node,
        cull_best_node: this.cull_best_node,
        mesh_ids: this.splitTrim(this.mesh_ids_text),
        strict_mesh_id_filtering: this.strict_mesh_id_filtering,
        const_c: this.const_c,
        const_tk: this.const_tk,
        user_timeout: this.user_timeout,
        two_way: this.two_way,
        shared_regulators: this.shared_regulators,
        terminal_ns: this.terminal_ns, // Pick from multi-select
        format: this.format,
      };
    },
    signValues() {
      return this.signOptions.map((obj) => obj.value)
    },
    weightValues() {
      return this.weightOptions.map((obj) => obj.value)
    },
    stmtFilterValues() {
      return this.stmtFilterOptions.map((obj) => obj.value)
    },
    nodeNamespaceValues() {
      return this.nodeNamespaceOptions.map((obj) => obj.value)
    },
    isContextSearch() {
      return this.mesh_ids_text.length > 0;
    },
    isNotOpenSearch() {
      return this.source.length > 0 && this.target.length > 0;
    },
    meshContextMissingMeshIds() {
      if (this.weighted !== "context") {
        return false;
      }
      const ids = this.splitTrim(this.mesh_ids_text).filter((id) => id.length > 0);
      return ids.length === 0;
    },
    meshIdsFieldErrors() {
      if (!this.meshContextMissingMeshIds || !this.meshIdsTouched) {
        return [];
      }
      return [
        {
          $uid: "mesh-context-requires-ids",
          $message:
            "At least one MeSH ID is required.",
        },
      ];
    },
    cannotSubmit() {
      /**
       * Flag if source/target are valid
       * **/
      // Source and target are both either of empty or filled only with whitespace
      const bothEmpty = this.source.length === 0 && this.target.length === 0
      // OR source contains only whitespace
      const srcWhiteSpace = !/\S/.test(this.source) && this.source.length > 0
      // OR target contains only whitespace
      const trgtWhiteSpace = !/\S/.test(this.target) && this.target.length > 0
      // OR source is not valid when filled
      const srcInvalid = this.source.length > 0 && !this.validSource
      // OR target is not valid when filled
      const trgtInvalid = this.target.length > 0 && !this.validTarget

      return (
        bothEmpty ||
        srcWhiteSpace ||
        trgtWhiteSpace ||
        srcInvalid ||
        trgtInvalid ||
        this.meshContextMissingMeshIds
      );
    },
    isContextWeighted() {
      return this.isContextSearch && !this.strict_mesh_id_filtering;
    },
    isAnyWeighted() {
      return (
        this.isContextWeighted || ["belief", "z_score"].includes(this.weighted)
      );
    },
    emptyResult() {
      const noPaths = sharedHelpers.isEmptyObject(this.results.path_results) || (
          this.results.path_results &&
          sharedHelpers.isEmptyObject(this.results.path_results.paths)
      )
      const noPathsRev = sharedHelpers.isEmptyObject(this.results.reverse_path_results) || (
          this.results.reverse_path_results &&
          sharedHelpers.isEmptyObject(this.results.reverse_path_results.paths)
      )
      const noOnt = sharedHelpers.isEmptyObject(this.results.ontology_results) || !(
          this.results.ontology_results.parents &&
          this.results.ontology_results.parents.length
      );
      const shrdTarg = sharedHelpers.isEmptyObject(this.results.shared_target_results) || !(
          this.results.shared_target_results.source_data &&
          this.results.shared_target_results.source_data.length
      );
      const shrdReg = sharedHelpers.isEmptyObject(this.results.shared_regulators_results) || !(
          this.results.shared_regulators_results.source_data &&
          this.results.shared_regulators_results.source_data.length
      );
      // console.log(`noPaths(${noPaths}) && noPathsRev(${noPathsRev}) && noOnt(${noOnt}) && shrdTarg(${shrdTarg}) && shrdReg(${shrdReg})`)
      return noPaths && noPathsRev && noOnt && shrdTarg && shrdReg;
    },
    generalErrors() {
      const bel = this.v$.belief_cutoff.$errors.length;
      const cull = this.v$.cull_best_node.$errors.length;
      const kShort = this.v$.k_shortest.$errors.length;
      const pLen = this.v$.path_length.$errors.length;
      return [bel, cull, kShort, pLen].reduce((ps, a) => ps + a, 0);
    },
    contextErrors() {
      const c = this.v$.const_c.$errors.length;
      const tk = this.v$.const_tk.$errors.length;
      const mesh =
        this.meshContextMissingMeshIds && this.meshIdsTouched ? 1 : 0;
      return [c, tk, mesh].reduce((ps, a) => ps + a, 0);
    },
    openErrors() {
      const mpn = this.v$.max_per_node.$errors.length;
      const dl = this.v$.depth_limit.$errors.length;
      return [mpn, dl].reduce((ps, a) => ps + a, 0);
    },
    strUUID() {
      return `form-id-${this.uuid}`;
    },
    accordionID() {
      return `accordion-${this.strUUID}`;
    },
    accordionIDObj() {
      return {
        accordionHeader1ID: `header1-${this.accordionID}`,
        accordionHeader2ID: `header2-${this.accordionID}`,
        accordionHeader3ID: `header3-${this.accordionID}`,
        accordionBody1ID: `body1-${this.accordionID}`,
        accordionBody2ID: `body2-${this.accordionID}`,
        accordionBody3ID: `body3-${this.accordionID}`,
      };
    },
  },
  methods: {
    touchMeshIds() {
      this.meshIdsTouched = true;
    },
    async sendForm() {
      const canSubmit = await this.v$.$validate();
      if (!canSubmit || this.cannotSubmit) {
        return false;
      }
      this.submissionError = null;
      this.isLoading = true;
      const currentQuery = this.networkSearchQuery;
      this.GStore.currentQuery = currentQuery;
      AxiosMethods.submitForm(currentQuery)
        .then((response) => {
          console.log("Query resolved!");
          console.log(response);
          this.results = response.data;
        })
        .catch((error) => {
          console.log(error);
          this.submissionError = error.toJSON();
          this.results = DefaultValues.EMPTY_RESULTS;
        })
        .then(() => {
          this.isLoading = false;
        });
    },
    splitTrim(inputText) {
      // Splits on comma and trims each item for whitespace, if empty
      // return empty array
      if (inputText) {
        return inputText.split(",").map((e) => {
          return e.trim();
        });
      } else {
        return [];
      }
    },
    isInOptions(varName, value) {
      let compareValues
      // Flag if a value is not in the options
      if (['terminal_ns', 'allowed_ns'].includes(varName)) {
        compareValues = this.nodeNamespaceValues
      } else if (varName === 'stmt_filter') {
        compareValues = this.stmtFilterValues
      } else if (varName === 'weighted') {
        compareValues = this.weightValues
      } else if (varName === 'sign') {
        // If '1' or '0' cast as number
        if (['0', '1'].includes(value)) {
          value = Number(value)
        }
        compareValues = this.signValues
      } else {
        return false
      }

      return compareValues.includes(value)
    },
    isInMultiOptions(varName, valArr) {
      let validValues = []
      for (const value of valArr) {
        if (!this.isInOptions(varName, value)) {
          // Flag for form error
          this.fillFormError = true
        } else {
          validValues.push(value)
        }
      }
      return validValues
    },
    fillMultiSel(varName, value) {
      let valArr
      if (value.constructor.name === 'Array') {
        valArr = value
      } else {
        valArr = [value]
      }

      let vvalArr = this.isInMultiOptions(varName, valArr)
      if (vvalArr){
        this.$data[varName] = vvalArr
      }
    },
    fillForm(urlQuery) {
      const fillMap = {
        source: "input",
        target: "input",
        stmt_filter: "multiselect",
        allowed_ns: "multiselect",
        node_blacklist: "input_join", // Join array to comma separated text
        path_length: "input",
        depth_limit: "input",
        sign: "select",
        weighted: "select",
        belief_cutoff: "input",
        curated_db_only: "checkbox",
        fplx_expand: "checkbox",
        k_shortest: "input",
        max_per_node: "input",
        cull_best_node: "input",
        mesh_ids: "input_join", // Join array to comma separated text
        strict_mesh_id_filtering: "checkbox",
        const_c: "input",
        const_tk: "input",
        user_timeout: "input",
        two_way: "checkbox",
        shared_regulators: "checkbox",
        terminal_ns: "multiselect",
      }

      // Loop key-method pairs present in fillMap
      for (const [key, fillType] of Object.entries(fillMap)) {
        // Only fill if key is present in urlQuery
        if (urlQuery[key]) {
          let value = urlQuery[key]
          // input:
          if (fillType === 'input') {
            this.$data[key] = value
            // Trigger prefix search when source/target are filled
            if (['source', 'target'].includes(key)) {
              let childRef
              if (key === 'source') {
                childRef = 'sourceComponent'
              } else {
                childRef = 'targetComponent'
              }
              this.$refs[childRef].getExternalAutoCompleteList(value)
            }
          } else if (fillType === 'select' && this.isInOptions(key, value)) {
            this.$data[key] = value
          } else if (fillType === 'input_join') {
            const formKey = key + '_text'
            let fillVal
            if (value.constructor.name === 'Array') {
              fillVal = value.join(', ')
            } else {
              fillVal = [value]
            }
            // Transform array to comma separated string
            this.$data[formKey] = fillVal
          // checkbox
          } else if (fillType === 'checkbox') {
            if (['true', 'false'].includes(value)) {
              value = Boolean(value)
            }
            if (typeof value === 'boolean') {
              this.$data[key] = value
            } else {
              console.log(`fillFormError for ${key}:${value}`)
              this.fillFormError = true
            }
          // multiselect (from vueform/multiselect)
          } else if (fillType === 'multiselect') {
            this.fillMultiSel(key, value)
          } else {
            console.log(`fillFormError for ${key}:${value}`)
            this.fillFormError = true
          }
        }
      }

      if (!this.fillFormError && !(urlQuery.execute === false || urlQuery.execute === 'false')) {
        this.querySearchExec = true // flag that it's ok to submit when source/target become valid
      } else if (this.fillFormError) {
        console.log('The form filled out incorrectly from query')
      } else if (urlQuery.execute === false || urlQuery.execute === 'false') {
        console.log('Query was set to not execute')
      }
    }
  },
  setup() {
    const uuid = UniqueID().getID();
    return {
      uuid,
      v$: useVuelidate(),
    };
  },
  mounted() {
    const urlQuery = this.$route.query;
    if (!sharedHelpers.isEmptyObject(urlQuery)) {
      this.fillForm(urlQuery)
    }
    return false;
  },
  watch: {
    weighted(newVal) {
      if (newVal !== "context") {
        this.meshIdsTouched = false;
      }
    },
    // Watch cannotSubmit and submit form if cannotSubmit === false
    cannotSubmit(newValue) {
      if (this.querySearchExec && newValue === false) {
        this.querySearchExec = false // disable this after first run
        this.sendForm()
      }
    },
  },
  validations() {
    return {
      source: {
        minLength: minLength(0),
        requiredIf: requiredIf(this.target.length === 0),
      },
      target: {
        minLength: minLength(0),
        requiredIf: requiredIf(this.source.length === 0),
      },
      k_shortest: {
        between: between(1, 50),
      },
      path_length: {
        minValue: minValue(1),
      },
      belief_cutoff: {
        between: between(0, 1),
      },
      cull_best_node: {
        freq: helpers.withMessage(
          "If provided, the minimum value allowed is 1.",
          cullFreq
        ),
      },
      const_c: {
        minValue: minValue(1),
      },
      const_tk: {
        minValue: minValue(1),
      },
      max_per_node: {
        minValue: minValue(1),
      },
      depth_limit: {
        minValue: minValue(1),
      },
      user_timeout: {
        between: between(2, 120),
      },
    };
  },
};
</script>

<style scoped>
.form-error {
  color: #a00000
}
</style>