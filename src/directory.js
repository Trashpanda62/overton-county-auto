(function (root) {
  "use strict";

  /* The filters hide listings that are already in the document. Nothing is
     fetched, nothing is injected, and nothing here is load-bearing: with
     scripting off the toolbar never appears and every county block, listing,
     phone number and address is on the page exactly as the server wrote it.

     Any failure inside the filter falls back to showing everything rather than
     leaving a half-filtered list on screen. A directory that quietly hides
     businesses is worse than one that does not filter at all. */

  var DEFAULTS = { county: "", category: "", gap: false, q: "" };

  function allowed(value, choices) {
    return choices.indexOf(value) !== -1 ? value : "";
  }

  function readState(search, choices) {
    var params = new URLSearchParams(search || "");
    return {
      county: allowed(params.get("county") || "", choices.counties),
      category: allowed(params.get("category") || "", choices.categories),
      gap: params.get("gap") === "1",
      q: (params.get("q") || "").trim().slice(0, 80)
    };
  }

  function stateSearch(state, currentSearch) {
    var params = new URLSearchParams(currentSearch || "");
    ["county", "category", "gap", "q"].forEach(function (name) { params.delete(name); });
    if (state.county) params.set("county", state.county);
    if (state.category) params.set("category", state.category);
    if (state.gap) params.set("gap", "1");
    if (state.q) params.set("q", state.q);
    var value = params.toString();
    return value ? "?" + value : "";
  }

  function matches(record, state) {
    var query = state.q.trim().toLowerCase();
    return (!state.county || record.county === state.county)
      && (!state.category || record.categories.indexOf(state.category) !== -1)
      && (!state.gap || record.gap)
      && (!query || record.haystack.indexOf(query) !== -1);
  }

  function values(select) {
    return Array.prototype.map.call(select.options, function (option) { return option.value; })
      .filter(function (value) { return value !== ""; });
  }

  function attach(document, window) {
    var toolbar = document.getElementById("toolbar");
    var county = document.getElementById("f-county");
    if (!toolbar || !county) return null;

    var category = document.getElementById("f-category");
    var gap = document.getElementById("f-gap");
    var text = document.getElementById("f-text");
    var reset = document.getElementById("f-reset");
    var emptyReset = document.getElementById("empty-reset");
    var count = document.getElementById("count");
    var empty = document.getElementById("empty");
    var error = document.getElementById("filter-error");
    var choices = { counties: values(county), categories: values(category) };

    var records = Array.prototype.map.call(
      document.querySelectorAll(".listing"),
      function (element) {
        return {
          element: element,
          county: element.getAttribute("data-county"),
          categories: (element.getAttribute("data-categories") || "").split(" "),
          gap: element.getAttribute("data-gap") === "1",
          haystack: (element.getAttribute("data-search") || "").toLowerCase()
        };
      }
    );
    var blocks = Array.prototype.slice.call(document.querySelectorAll(".county-block"));

    function controlsState() {
      return {
        county: county.value,
        category: category.value,
        gap: gap.checked,
        q: text.value.trim().slice(0, 80)
      };
    }

    function setControls(state) {
      county.value = state.county;
      category.value = state.category;
      gap.checked = state.gap;
      text.value = state.q;
    }

    function render(state) {
      var shown = 0;
      records.forEach(function (item) {
        var visible = matches(item, state);
        item.element.hidden = !visible;
        if (visible) shown += 1;
      });
      blocks.forEach(function (block) {
        var any = block.querySelector(".listing:not([hidden])");
        block.hidden = !any;
      });
      count.textContent = shown === records.length
        ? "Showing all " + records.length + " businesses"
        : "Showing " + shown + " of " + records.length + " businesses";
      empty.classList.toggle("on", shown === 0);
      error.hidden = true;
      toolbar.setAttribute(
        "data-filtered",
        String(Boolean(state.county || state.category || state.gap || state.q))
      );
      return shown;
    }

    function recover() {
      records.forEach(function (item) { item.element.hidden = false; });
      blocks.forEach(function (block) { block.hidden = false; });
      count.textContent = "Showing all " + records.length + " businesses";
      empty.classList.remove("on");
      error.hidden = false;
      toolbar.setAttribute("data-filtered", "false");
    }

    function update(method) {
      var state = controlsState();
      render(state);
      var target = window.location.pathname + stateSearch(state, window.location.search)
        + window.location.hash;
      window.history[method + "State"]({ directory: state }, "", target);
    }

    function safely(method) {
      try { update(method); } catch (failure) { recover(); }
    }

    [county, category, gap].forEach(function (control) {
      control.addEventListener("change", function () { safely("push"); });
    });
    text.addEventListener("input", function () { safely("replace"); });
    reset.addEventListener("click", function () {
      setControls(DEFAULTS);
      safely("push");
      text.focus();
    });
    if (emptyReset) {
      emptyReset.addEventListener("click", function () { reset.click(); });
    }
    window.addEventListener("popstate", function () {
      setControls(readState(window.location.search, choices));
      try { render(controlsState()); } catch (failure) { recover(); }
    });

    toolbar.hidden = false;
    setControls(readState(window.location.search, choices));
    safely("replace");
    return { render: render, state: controlsState };
  }

  var api = { DEFAULTS: DEFAULTS, readState: readState, stateSearch: stateSearch,
    matches: matches, attach: attach };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root && root.document) attach(root.document, root);
}(typeof window !== "undefined" ? window : null));
