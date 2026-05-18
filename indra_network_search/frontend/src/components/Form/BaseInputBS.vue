<template>
  <div class="form-floating">
    <input
      v-bind="$attrs"
      :id="strUUID"
      :value="modelValue"
      :placeholder="ph"
      :title="compTitle"
      @blur="$emit('blur', $event)"
      @input="$emit('update:modelValue', $event.target.value)"
      class="form-control"
    />
    <label :for="strUUID" class="form-label" v-if="label">{{ label }}</label>
    <template v-if="errors.length > 0 || hasWhitespaceError">
      <p v-for="error in errors" :key="error.$uid" style="color: #a00000">
        {{ error.$message ? error.$message : "Invalid entry" }}
      </p>
      <p v-if="hasWhitespaceError" style="color: #a00000">
        Check input for whitespace
      </p>
    </template>
  </div>
</template>

<script>
import UniqueID from "@/helpers/BasicHelpers";

export default {
  emits: ["update:modelValue", "blur"],
  props: {
    label: {
      type: String,
      default: "",
    },
    modelValue: {
      type: [String, Number],
      default: "",
    },
    placeholder: {
      type: String,
      default: "",
    },
    title: {
      type: String,
      default: "",
    },
    errors: {
      type: Array,
      default: () => {
        return [];
      },
    },
    allowWhitespace: {
      type: Boolean,
      default: true,
    },
  },
  setup() {
    const uuid = UniqueID().getID();
    return {
      uuid,
    };
  },
  computed: {
    strUUID() {
      return `input${this.uuid}`;
    },
    ph() {
      return this.placeholder || this.label;
    },
    compTitle() {
      return this.title || this.ph;
    },
    hasWhitespaceError() {
      return (
        !this.allowWhitespace &&
        this.modelValue.length > 0 &&
        !/\S/.test(this.modelValue)
      );
    },
  },
};
</script>
