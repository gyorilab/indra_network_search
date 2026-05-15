<template>
  <div class="node-blacklist-async-ms" @focusout="onFocusOut">
    <Multiselect
      :model-value="modelValue"
      mode="tags"
      :placeholder="placeholder"
      :title="title"
      :disabled="disabled"
      :searchable="true"
      :create-tag="false"
      :options="nodeBlacklistOptions"
      :filter-results="false"
      :delay="250"
      :min-chars="1"
      :resolve-on-load="false"
      value-prop="value"
      label="label"
      @update:model-value="$emit('update:modelValue', $event)"
    />
    <template v-if="errors.length > 0">
      <p v-for="error in errors" :key="error.$uid" style="color: #a00000">
        {{ error.$message ? error.$message : "Invalid entry" }}
      </p>
    </template>
  </div>
</template>

<script>
import Multiselect from "@vueform/multiselect";
import AxiosMethods from "@/services/AxiosMethods";

export default {
  name: "NodeBlacklistAsyncMultiselect",
  components: { Multiselect },
  props: {
    modelValue: {
      type: Array,
      default: () => [],
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    errors: {
      type: Array,
      default: () => [],
    },
    placeholder: {
      type: String,
      default: "Node blacklist",
    },
    title: {
      type: String,
      default:
        "Start typing to search nodes from the graph to add to the blacklist",
    },
  },
  emits: ["update:modelValue", "blur"],
  methods: {
    async nodeBlacklistOptions(query) {
      const q = (query || "").trim();
      if (!q) {
        return [];
      }
      try {
        const res = await AxiosMethods.auto(q);
        const rows = res.data || [];
        return rows.map(([name, namespace, identifier]) => ({
          value: name,
          label: `${name} — ${namespace}:${identifier}`,
        }));
      } catch (e) {
        console.log("autocomplete (node blacklist) failed", e);
        return [];
      }
    },
    onFocusOut(event) {
      const root = event.currentTarget;
      if (root && !root.contains(event.relatedTarget)) {
        this.$emit("blur", event);
      }
    },
  },
};
</script>
