<template>
  <div
    class="form-check"
    :class="[
      verticalAlignment.length ? verticalAlignment : '',
      horizontalAlignment.length ? horizontalAlignment : '',
    ]"
  >
    <input
      class="form-check-input"
      type="checkbox"
      v-bind="$attrs"
      :checked="modelValue"
      @change="$emit('update:modelValue', $event.target.checked)"
      :id="strUUID"
    />
    <label v-if="label" class="form-check-label" :for="strUUID">{{
      label
    }}</label>
    <template v-if="errors.length > 0">
      <p v-for="error in errors" :key="error.$uid" style="color: #a00000">
        {{ error.$message ? error.$message : "Invalid entry" }}
      </p>
    </template>
  </div>
</template>

<script>
import UniqueID from "@/helpers/BasicHelpers";

export default {
  props: {
    label: {
      type: String,
      default: "",
    },
    modelValue: {
      type: Boolean,
      default: false,
    },
    errors: {
      type: Array,
      default: () => {
        return [];
      },
    },
    verticalAlignment: {
      type: String,
      default: "",
    },
    horizontalAlignment: {
      type: String,
      default: "",
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
      return `checkbox${this.uuid}`;
    },
  },
};
</script>
