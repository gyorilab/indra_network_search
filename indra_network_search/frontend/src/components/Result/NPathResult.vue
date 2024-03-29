<template>
  <div class="card text-center">
    <div class="card-header">
      <div class="d-flex justify-content-between">
        <h4>
          <!-- Header N-edge paths | Source -> {X_n} -> target | source badges | collapse toggle icon -->
          {{ edgeCount }}-edge paths;
          <template v-if="sourceExist"><NodeModal v-bind="source" /></template>
          <template v-else>source</template>
          <i class="bi bi-arrow-right"></i>
          <template v-for="n in edgeCount - 1" :key="n">
            X{{ n }}<i class="bi bi-arrow-right"></i>
          </template>
          <template v-if="targetExist"><NodeModal v-bind="target" /></template>
          <template v-else>target</template>
          <span
            style="margin-left: 10px"
            class="badge rounded-pill bg-primary"
            :title="`${pathArray.length} paths found`"
            >{{ pathArray.length }}</span
          >
        </h4>
        <a
          role="button"
          data-bs-toggle="collapse"
          :href="`#${strUUID}`"
          :aria-expanded="false"
          :aria-controls="strUUID"
          @click="toggleShowFlag()"
        >
          <i
            v-if="isExpanded"
            title="Click to collapse"
            class="bi-dash-circle fs-4"
          ></i>
          <i v-else title="Click to expand" class="bi-plus-circle fs-4"></i>
        </a>
      </div>
    </div>
    <div class="card-body collapse show" :id="strUUID">
      <!-- Table (or grid) with two columns: Path | Support -->
      <div class="container">
        <table class="table" style="width: 100%">
          <col style="width: 25%" />
          <col style="width: 75%" />
          <thead>
            <tr>
              <th scope="col">Path</th>
              <th scope="col">Support</th>
            </tr>
          </thead>
          <tbody>
            <!-- v-for loop over table/grid rows: <Path />; <Path /> currently assumes
               a table encapsulating it -->
            <tr v-for="(path, index) in pathArray" :key="index">
              <Path v-bind="path" />
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import sharedHelpers from "@/helpers/sharedHelpers";
import NodeModal from "@/components/Result/NodeModal";
import Path from "@/components/Result/Path";
import UniqueID from "@/helpers/BasicHelpers";

export default {
  components: { Path, NodeModal },
  props: {
    // Follows one entry in
    // indra_network_search.data_models::PathResultData.paths: Dict[int, List[Path]]
    pathNodeCount: {
      type: [Number, String],
      required: true,
    },
    source: {
      type: Object,
      default: null,
      validator: (obj) => {
        return sharedHelpers.isOptionalNode(obj);
      },
    },
    target: {
      type: Object,
      default: null,
      validator: (obj) => {
        return sharedHelpers.isOptionalNode(obj);
      },
    },
    pathArray: {
      type: Array,
      required: true,
      validator: (arr) => {
        // Check if array and array of Path
        const isArr = Array.isArray(arr);
        // TodO: Find out why 'arr.every(sharedHelpers.isNodeArray)' errors with:
        //  "Uncaught TypeError: arr.every is not a function"
        // console.log('isArr=', isArr);
        // console.log('typeof=', typeof arr);
        // console.log(arr);
        // return isArr && arr.every(sharedHelpers.isNodeArray);
        return isArr;
      },
    },
  },
  created() {
    // Throw error if source && target are null
    if (this.source === null && this.target === null) {
      throw Error("Must provide at least one of source and target as props");
    }
  },
  setup() {
    const uuid = UniqueID().getID();
    return {
      uuid,
    };
  },
  methods: {
    toggleShowFlag() {
      this.isExpanded = !this.isExpanded;
    },
  },
  data() {
    return {
      isExpanded: true, // Fixme: set this by reading classList from tags
    };
  },
  computed: {
    sourceExist() {
      return this.source !== null;
    },
    targetExist() {
      return this.target !== null;
    },
    pathNodeCountNum() {
      return Number(this.pathNodeCount);
    },
    edgeCount() {
      return this.pathNodeCountNum - 1;
    },
    strUUID() {
      return `collapse-${this.uuid}`;
    },
  },
};
</script>
