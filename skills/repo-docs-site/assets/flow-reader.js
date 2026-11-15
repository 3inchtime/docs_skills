/* Reading controls only: the diagram remains the source of control flow. */
(() => {
  'use strict';
  if (customElements.get('repo-flow-reader')) return;

  class RepoFlowReader extends HTMLElement {
    connectedCallback() {
      if (this._ready) return;
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.connectedCallback(), { once: true });
        return;
      }
      const belongsHere = (element) => element.closest('repo-flow-reader') === this;
      const steps = [...this.querySelectorAll('[data-flow-step]')].filter(belongsHere);
      const controls = [...this.querySelectorAll('[data-flow-controls]')].find(belongsHere);
      const previous = [...this.querySelectorAll('[data-flow-prev]')].find(belongsHere);
      const next = [...this.querySelectorAll('[data-flow-next]')].find(belongsHere);
      const status = [...this.querySelectorAll('[data-flow-status]')].find(belongsHere);
      const selectors = steps.map((step) => step.querySelector('[data-flow-select]'));
      const nodeIds = steps.map((step) => step.dataset.nodeId);

      if (!steps.length || !controls || !previous || !next || !status ||
          selectors.some((button) => !button) || nodeIds.some((id) => !id) ||
          new Set(nodeIds).size !== nodeIds.length) {
        // Leave the complete static content intact when the contract is incomplete.
        return;
      }

      this._ready = true;
      let current = 0;
      const select = (index) => {
        current = Math.max(0, Math.min(index, steps.length - 1));
        steps.forEach((step, position) => {
          const active = position === current;
          step.classList.toggle('flow-current', active);
          if (active) selectors[position].setAttribute('aria-current', 'step');
          else selectors[position].removeAttribute('aria-current');
        });
        previous.disabled = current === 0;
        next.disabled = current === steps.length - 1;
        status.textContent = `说明 ${current + 1} / ${steps.length}：${selectors[current].textContent.trim()}`;
      };

      previous.addEventListener('click', () => select(current - 1));
      next.addEventListener('click', () => select(current + 1));
      selectors.forEach((button, index) => {
        button.addEventListener('click', () => select(index));
        button.disabled = false;
      });
      controls.hidden = false;
      select(0);
    }
  }

  customElements.define('repo-flow-reader', RepoFlowReader);
})();
