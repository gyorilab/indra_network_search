<template>
  <div class="mesh-ids-async-ms" @focusout="onFocusOut">
    <label v-if="label" class="form-label small text-muted mb-1 d-block">{{
      label
    }}</label>
    <Multiselect
      :model-value="modelValue"
      mode="tags"
      :placeholder="placeholder"
      :title="title || placeholder"
      :disabled="disabled"
      :searchable="true"
      :create-tag="false"
      :options="meshOptions"
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
  name: "MeshIdsAsyncMultiselect",
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
    label: {
      type: String,
      default: "Mesh IDs",
    },
    placeholder: {
      type: String,
      default: "Search MeSH by name, then select",
    },
    title: {
      type: String,
      default: "",
    },
  },
  emits: ["update:modelValue", "blur"],
  methods: {
    async meshOptions(query) {
      const q = (query || "").trim();
      if (!q) {
        return [];
      }
      try {
        const res = await AxiosMethods.autocompleteMesh(q);
        const rows = res.data || [];
        return rows.map(([name, identifier]) => ({
          value: identifier,
          label: `${name} (${identifier})`,
        }));
      } catch (e) {
        console.log("autocompleteMesh failed", e);
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
