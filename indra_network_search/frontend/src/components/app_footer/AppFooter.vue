<template>
  <div class="container my-2" id="footer-container">
    <footer class="footer text-muted" id="about">
      <h5 class="me-md-auto font-weight-normal fs-2" id="about-header">About</h5>
      <small>
        <ul class="list-unstyled justify-content-start">
          <li class="float-end">
            <a href="#">Back to top</a>
          </li>
          <li>This software is developed by the <a href="https://gyorilab.github.io/" target="_blank">Gyori Lab for Computational Biomedicine</a> at Northeastern University</li>
          <li>This work was funded by DARPA grant W911NF018-1-0124 under the DARPA ASDF program.</li>
        </ul>
      </small>
    </footer>
  </div>
</template>

<script>
export default {
  name: "Footer.vue"
}
</script>

<style scoped>
#footer-container {
  background: #F5F5F5;
  text-align: start;
}

#about-header {
  text-align: center;
}
</style>
