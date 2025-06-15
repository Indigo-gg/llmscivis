<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-stepper v-model="step" vertical>
          <v-step :complete="step > 1" title="Inquiry expansion">
            <v-card>
              <v-card-title>Step 1: Inquiry expansion</v-card-title>
              <v-card-text>
                This is the first step of the workflow.
              </v-card-text>
            </v-card>
          </v-step>

          <v-step :complete="step > 2" title="RAG">
            <v-card>
              <v-card-title>Step 2: RAG</v-card-title>
              <v-card-text>
                This is the second step of the workflow.
              </v-card-text>
            </v-card>
          </v-step>

          <v-step title="Iterative loop">
            <v-card>
              <v-card-title>Step 3: Iterative loop</v-card-title>
              <v-card-text>
                This is the final step of the workflow.
              </v-card-text>
            </v-card>
          </v-step>
        </v-stepper>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
export default {
  data() {
    return {
      step: 1,
    };
  },
};
</script>

<style scoped>
/* Add any specific styles here */
</style>
