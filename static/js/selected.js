document.addEventListener("DOMContentLoaded", function() {
  const selectBASIC = document.getElementById("id_race_basic_0");
  const selectHORSE = document.getElementById("id_past_horse_0");
  const selectJOCKEY = document.getElementById("id_past_jockey_0");
  const selectRESULT = document.getElementById("id_result_info_0");
  const checkboxesBASIC = document.querySelectorAll("#id_race_basic input[type='checkbox']:not(#id_race_basic_0)");
  const checkboxesHORSE = document.querySelectorAll("#id_past_horse input[type='checkbox']:not(#id_past_horse_0)");
  const checkboxesJOCKEY = document.querySelectorAll("#id_past_jockey input[type='checkbox']:not(#id_past_jockey_0)");
  const checkboxesRESULT = document.querySelectorAll("#id_result_info input[type='checkbox']:not(#id_result_info_0)");

  selectBASIC.addEventListener("change", function() {
    checkboxesBASIC.forEach(cb => cb.checked = selectBASIC.checked);
  });
  selectHORSE.addEventListener("change", function() {
    checkboxesHORSE.forEach(cb => cb.checked = selectHORSE.checked);
  });
  selectJOCKEY.addEventListener("change", function() {
    checkboxesJOCKEY.forEach(cb => cb.checked = selectJOCKEY.checked);
  });
  selectRESULT.addEventListener("change", function() {
    checkboxesRESULT.forEach(cb => cb.checked = selectRESULT.checked);
  });

  // 子のチェックボックスを操作したとき、全選択状態も更新する
  checkboxesBASIC.forEach(cb => {
    cb.addEventListener("change", function() {
      // 全てONなら「全選択」もON、そうでなければOFF
      const allCheckedBASIC = Array.from(checkboxesBASIC).every(cb => cb.checked);
      checkboxesBASIC.checked = allCheckedBASIC;
    });
  });

    // 子のチェックボックスを操作したとき、全選択状態も更新する
  checkboxesHORSE.forEach(cb => {
    cb.addEventListener("change", function() {
      // 全てONなら「全選択」もON、そうでなければOFF
      const allCheckedHORSE = Array.from(checkboxesHORSE).every(cb => cb.checked);
      checkboxesHORSE.checked = allCheckedHORSE;
    });
  });

    // 子のチェックボックスを操作したとき、全選択状態も更新する
  selectJOCKEY.forEach(cb => {
    cb.addEventListener("change", function() {
      // 全てONなら「全選択」もON、そうでなければOFF
      const allCheckedJOCKEY = Array.from(selectJOCKEY).every(cb => cb.checked);
      selectJOCKEY.checked = allCheckedJOCKEY;
    });
  });

    // 子のチェックボックスを操作したとき、全選択状態も更新する
  selectRESULT.forEach(cb => {
    cb.addEventListener("change", function() {
      // 全てONなら「全選択」もON、そうでなければOFF
      const allCheckedRESULT = Array.from(selectRESULT).every(cb => cb.checked);
      selectRESULT.checked = allCheckedRESULT;
    });
  });
});

function toggleAll(check) {
  const checkboxes = document.querySelectorAll('.checkbox-font');
  checkboxes.forEach(cb => cb.checked = check);
}