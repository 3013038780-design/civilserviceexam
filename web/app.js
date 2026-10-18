'use strict';
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const PUBLIC = window.STUDY_PUBLIC || {docs:[],assets:{}};
  const methodOf=n=>n<=20?'politics':n<=35?'knowledge':n<=45?'cloze':n<=55?'structure':n<=65?'reading':n<=80?'quantity':n<=90?'figures':n<=100?'definition':n<=105?'analogy':n<=115?'logic':'data';
  const moduleOf = n => n<=20?'政治理论':n<=35?'常识判断':n<=65?'言语理解':n<=80?'数量关系':n<=90?'图形推理':n<=100?'定义判断':n<=105?'类比推理':n<=115?'逻辑判断':'资料分析';
  let records = {favorites:[],notes:{},practice:{},font:18}, bundle = null, noteTimer, toastTimer;
  try { const old = JSON.parse(localStorage.getItem('gongkao-reader-records-v1') || 'null'); if(old && Array.isArray(old.favorites) && old.notes && typeof old.notes==='object') records={...records,...old,font:Math.min(24,Math.max(16,Number(old.font)||18))}; } catch{}
  const state = {module:'全部模块',filter:'all',search:'',q:117,path:0,reveal:true,shenlun:1};
  function toast(s){ $('#toast').textContent=s;$('#toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),3500); }
  function saveRecords(){try{localStorage.setItem('gongkao-reader-records-v1',JSON.stringify(records));return true;}catch{toast('浏览器未允许保存，请及时导出笔记。');return false;}}
  function setFont(){document.documentElement.style.setProperty('--reading',records.font+'px');$('#font-label').textContent=records.font;}
  function db(){return new Promise((resolve,reject)=>{if(!window.indexedDB)return reject(Error('无法缓存'));const r=indexedDB.open('gongkao-reader-v1',1);r.onupgradeneeded=()=>r.result.createObjectStore('data');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
  async function cachedBundle(value){const d=await db();try{return await new Promise((resolve,reject)=>{const t=d.transaction('data',value?'readwrite':'readonly');const s=t.objectStore('data');const r=value?s.put(value,'bundle'):s.get('bundle');r.onsuccess=()=>{if(!value)resolve(r.result);};t.oncomplete=()=>{if(value)resolve(true);};t.onerror=()=>reject(t.error);});}finally{d.close();}}
  const fields=['题型','读题信号与阅读重点','停止条件','边界与迁移提醒','首答','机构参考','本轮工作答案'];
  const practiceImage=s=>typeof s==='string'&&(/^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(s)||/^practice-images\/[a-f0-9]{24}\.(jpg|png|webp)$/.test(s));
  function validateBundle(o){
    if(!o || o.schema!=='gongkao-study/v1' || !Array.isArray(o.xingce)||o.xingce.length!==135 ||!Array.isArray(o.shenlun)||o.shenlun.length!==5)throw Error('请选择本项目生成的完整学习资料包（135题行测、5题申论）。');
    const validImage=s=>typeof s==='string'&&(/^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(s)||/^paper-images\/[a-f0-9]{24}\.jpg$/.test(s));
    const ids = new Set();for(const q of o.xingce){if(q.questionImage&&!validImage(q.questionImage)||q.contextImage&&!validImage(q.contextImage)||q.questionText&&typeof q.questionText!=='string')throw Error('题面图片或文字格式不受支持。');if(!Number.isInteger(q.题号)||q.题号<1||q.题号>135||ids.has(q.题号)||fields.some(k=>typeof q[k]!=='string'||q[k].length>30000)||!Array.isArray(q.教学路径)||q.教学路径.length<1||q.教学路径.length>3||q.教学路径.some(v=>typeof v!=='string'||v.length>30000))throw Error('资料包的题目字段不完整，原有资料未更改。');ids.add(q.题号);if(!['A','B','C','D'].includes(q.首答)||!['A','B','C','D'].includes(q.机构参考))throw Error('选项格式无效。');}
    if(o.shenlun.some((q,i)=>q.题号!==i+1||typeof q.首答!=='string'))throw Error('申论资料字段无效。');
    if(!o.paper || !Array.isArray(o.paper.pages)||o.paper.pages.length!==26 ||o.paper.pages.some(s=>!validImage(s)))throw Error('原题页图缺失或格式不受支持。');
    if(!o.paper.map || o.xingce.some(q=>!Number.isInteger(o.paper.map[q.题号]?.page)||o.paper.map[q.题号].page<1||o.paper.map[q.题号].page>26))throw Error('原题页码无效。');
    if(o.crossYearExamples&&(!Array.isArray(o.crossYearExamples)||o.crossYearExamples.some(x=>!x||typeof x.id!=='string'||typeof x.title!=='string'||typeof x.execution!=='string'||!Array.isArray(x.methods)||!Array.isArray(x.years)||!['data','definition','structure'].includes(x.category)||!['已有策略检验','存在争议'].includes(x.status))))throw Error('跨年题例字段不完整。');
    if(o.strategyPractice)for(const p of Object.values(o.strategyPractice)){
      if(p?.mode!=='guided-transfer/v1')continue;
      if(!Array.isArray(p.questions)||p.questions.length<3||p.questions.length>5||p.questions.some(q=>!q||typeof q.source_id!=='string'||typeof q.label!=='string'||typeof q.hint!=='string'||!(practiceImage(q.image)||(typeof q.questionText==='string'&&q.questionText.length>0&&q.questionText.length<10000))))throw Error('试用题字段或原图格式无效。');
    }
    if(o.strategyPracticeReview)for(const group of Object.values(o.strategyPracticeReview))for(const v of Object.values(group))if(!v||!['A','B','C','D'].includes(v.answer)||typeof v.execution!=='string'||!(v.kind==='self-authored'&&typeof v.proof_id==='string'||/^review-[a-f0-9]{14}$/.test(v.review_id)))throw Error('试用核验字段无效。');
    return o;
  }
  function safeURL(s){try{const u=new URL(s);return u.protocol==='https:'?u.href:null;}catch{return null;}}
  function resolveDoc(url,doc){const clean=url.split('#')[0];if(!clean)return '#'+url;let p;try{p=new URL(clean,'https://local.invalid/'+(doc?.path||'')).pathname.slice(1);}catch{return null;}const found=PUBLIC.docs.find(d=>d.path===decodeURIComponent(p));return found?'#/doc/'+found.id:null;}
  function inline(s,doc){let text=esc(s);const slots=[];const hold=h=>{slots.push(h);return '\u0001'+(slots.length-1)+'\u0002';};
    text=text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g,(_,alt,url)=>{let p=url.replace(/^&lt;|&gt;$/g,'');try{p=decodeURIComponent(new URL(p,'https://local.invalid/'+(doc?.path||'')).pathname.slice(1));}catch{}const src=PUBLIC.assets[p];return hold(src?`<img src="${esc(src)}" alt="${alt}" loading="lazy">`:`<span class="subtle">图示：${alt}</span>`);});
    text=text.replace(/\[([^\]]+)\]\(([^)]+)\)/g,(_,label,u)=>{let url=u.replace(/^&lt;|&gt;$/g,'');const internal=resolveDoc(url,doc);const external=safeURL(url);return hold(internal?`<a href="${esc(internal)}">${label}</a>`:external?`<a href="${esc(external)}" target="_blank" rel="noopener noreferrer">${label} ↗</a>`:`<span>${label}</span>`);});
    text=text.replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
    return text.replace(/\u0001(\d+)\u0002/g,(_,i)=>slots[+i]);
  }
  function markdown(src,doc){const lines=String(src||'').replace(/\r/g,'').split('\n');let out='',i=0,heading=0;while(i<lines.length){let l=lines[i];if(!l.trim()){i++;continue;}if(l.startsWith('```')){let b=[];i++;while(i<lines.length&&!lines[i].startsWith('```'))b.push(lines[i++]);i++;out+='<pre><code>'+esc(b.join('\n'))+'</code></pre>';continue;}
    let m=l.match(/^(#{1,4})\s+(.+)/);if(m){const n=m[1].length;out+=`<h${n} id="heading-${heading++}">${inline(m[2],doc)}</h${n}>`;i++;continue;}
    if(l.trim().startsWith('|')&&i+1<lines.length&&/^\s*\|?[\s:|-]+\|/.test(lines[i+1])){let rows=[];rows.push(l);i+=2;while(i<lines.length&&lines[i].trim().startsWith('|'))rows.push(lines[i++]);out+='<div class="table-wrap"><table>'+rows.map((r,n)=>'<tr>'+r.trim().replace(/^\||\|$/g,'').split('|').map(c=>`<${n?'td':'th'}>${inline(c.trim(),doc)}</${n?'td':'th'}>`).join('')+'</tr>').join('')+'</table></div>';continue;}
    if(/^\s*[-*]\s+/.test(l)||/^\d+\.\s+/.test(l)){const ordered=/^\d+\./.test(l),tag=ordered?'ol':'ul';out+='<'+tag+'>';while(i<lines.length&&(/^\s*[-*]\s+/.test(lines[i])||/^\d+\.\s+/.test(lines[i]))){out+='<li>'+inline(lines[i++].replace(/^\s*(?:[-*]|\d+\.)\s+/,''),doc)+'</li>';}out+='</'+tag+'>';continue;}
    if(l.startsWith('>')){out+='<blockquote>'+inline(l.replace(/^>\s?/,''),doc)+'</blockquote>';i++;continue;}
    const p=[l];i++;while(i<lines.length&&lines[i].trim()&&!/^(?:#{1,4}\s|```|\||[-*]\s|\d+\.\s|>)/.test(lines[i]))p.push(lines[i++]);out+='<p>'+inline(p.join('\n'),doc).replace(/\n/g,'<br>')+'</p>';}
    return out;
  }
  function route(){const p=location.hash.replace(/^#\/?/,'').split('/');return {view:p[0]||'xingce',id:p[1],branch:p[2]};}
  function go(view,id){const next='#/'+view+(id?'/'+id:'');if(location.hash===next)render();else location.hash=next;$('#sidebar').classList.remove('open');$('#menu-button').setAttribute('aria-expanded','false');}
  function allQuestions(){return bundle?bundle.xingce:[];}
  function filtered(){const term=state.search.trim().toLowerCase().replace(/^第|题$/g,'');return allQuestions().filter(q=>(state.module==='全部模块'||moduleOf(q.题号)===state.module)&&(state.filter==='all'||state.filter==='wrong'&&q.首答!==q.机构参考||state.filter==='saved'&&records.favorites.includes(q.题号)||state.filter==='recommended'&&[117,118,54,93].includes(q.题号))&&(!term||String(q.题号)===term||[q.题型,q.读题信号与阅读重点].join(' ').toLowerCase().includes(term)));}
  function moduleMenu(){const names=['全部模块','政治理论','常识判断','言语理解','数量关系','图形推理','定义判断','类比推理','逻辑判断','资料分析'];$('#module-list').innerHTML=names.map(n=>`<button class="module-button ${n===state.module?'active':''}" data-module="${n}"><span>${n}${['数量关系','图形推理'].includes(n)?' · 暂缓专项':''}</span><em>${n==='全部模块'?135:allQuestions().filter(q=>moduleOf(q.题号)===n).length||({'政治理论':20,'常识判断':15,'言语理解':30,'数量关系':15,'图形推理':10,'定义判断':10,'类比推理':5,'逻辑判断':10,'资料分析':20}[n])}</em></button>`).join('');}
  function banner(k,title,desc,chip=''){return `<div class="intro-row"><div><p class="page-kicker">${k}</p><h1 class="page-title">${title}</h1><p class="page-intro">${desc}</p></div>${chip?`<span class="status-chip">${chip}</span>`:''}</div>`;}
  function empty(){return `<section class="empty"><div class="eyebrow">完整资料只在你的设备</div><h2>把学习资料放进来，就能开始研习。</h2><p>在线界面已经准备好。请选择本项目生成的 <code>公考学习资料包.json</code>，即可阅读135题行测、五题申论和原题图。文件由浏览器直接读取，不上传到服务器。</p><button class="primary" data-import>选择本机学习资料包</button><p class="subtle">也可以打开本机的“公考解题研习室.html”，内容已预装。现在仍可直接阅读方法卡与公开资料。</p></section>`;}
  function strip(){const qs=filtered();$('#question-strip').innerHTML=qs.length?qs.map(q=>`<button class="q-dot ${q.题号===state.q?'active':''} ${records.favorites.includes(q.题号)?'marked':''}" data-q="${q.题号}" aria-label="第${q.题号}题" aria-pressed="${q.题号===state.q}">${q.题号}</button>`).join(''):'<span class="no-results">没有匹配题目。试试题号或放宽筛选。</span>';$('#result-count').textContent=qs.length+' 题';$('#question-strip .active')?.scrollIntoView({block:'nearest',inline:'nearest'});}
  function lesson(q){const n=q.题号,saved=records.favorites.includes(n),m=bundle.paper.map[n],source=bundle.paper.pages[m.page-1];
    return `<div class="lesson-head"><div><div class="lesson-tag">2026 副省级 · ${moduleOf(n)}</div><h2>第 ${n} 题 <span class="muted">/</span> ${esc(q.题型.split('·').slice(1).join(' · ')||q.题型)}</h2></div><div class="lesson-actions"><button id="bookmark" class="${saved?'saved':''}" aria-pressed="${saved}">${saved?'★ 已收藏':'☆ 稍后再看'}</button><button id="reveal-toggle">${state.reveal?'先自己想':'查看解法'}</button></div></div><div class="lesson-layout"><section class="panel"><div class="panel-bar"><strong>对照原题</strong><span>原卷第 ${m.page} 页</span></div><div class="paper-content">${q.questionText?`<div class="question-text">${esc(q.questionText)}</div><p class="source-note">文字由原卷提取，图表、空格与公式以原卷图为准。</p>`:''}${q.contextImage?`<div class="eyebrow">本组资料 · 点图放大</div><img class="source-thumb" src="${q.contextImage}" alt="第${n}题所在题组资料" data-zoom><div class="source-caption">保留原卷图表，便于核对单位、时间与口径。</div>`:''}${q.questionImage?`<details ${!q.questionText||n>=81&&n<=90?'open':''}><summary>查看原题裁片（含图形与选项）</summary><img class="source-thumb" src="${q.questionImage}" alt="第${n}题原题裁片" data-zoom></details>`:''}<div class="source-controls"><button data-full-page="${m.page}">放大原卷整页 ↗</button>${m.page>1?`<button data-full-page="${m.page-1}">上一页材料</button>`:''}${m.page<26?`<button data-full-page="${m.page+1}">下一页／跨页选项</button>`:''}</div><div class="source-note">只读原始题面，不重新编排图形。题目跨页时可查看相邻页。</div></div></section><section class="panel"><div class="panel-bar"><strong>这道题，怎样判断</strong><span>${q.首答===q.机构参考?'AI首答与参考一致':'保留首答与修正'}</span></div><div class="method-body"><button class="soft wide" data-method="${methodOf(n)}">先学这一类的通用方法 →</button>${state.reveal?method(q):`<div class="reveal-cover">先确定问题问什么、需要哪条依据，以及选出答案要算到哪一步。<br>这里不计分，也不要求先测试才能学习。<br><button class="primary" data-reveal>展开这道题的解法</button></div>`}</div></section></div><div class="note-area"><label for="question-note">这一题，我想带走的一个动作</label><textarea id="question-note" placeholder="例如：先把时间口径对齐，再看选项决定计算精度。">${esc(records.notes['x'+n]||'')}</textarea><div class="note-footer"><span id="note-status">只保存在当前浏览器，不自动同步</span><button id="save-note">保存笔记</button></div></div><div class="bottom-nav"><button id="prev-question">← 上一题</button><span>可以用键盘 ← → 换题；不要求每题执行所有路径。</span><button id="next-question">下一题 →</button></div>`;
  }
  function method(q){state.path=Math.min(state.path,q.教学路径.length-1);return `<section class="step"><h3 class="step-heading"><span class="step-number">01</span>先看哪里，为什么选这个方法</h3><div class="reading">${inline(q.读题信号与阅读重点)}</div></section><section class="step"><h3 class="step-heading"><span class="step-number">02</span>先学这一条，再比较其他入口</h3><div class="path-tabs" role="group" aria-label="解题路径">${q.教学路径.map((_,i)=>`<button data-path="${i}" class="${i===state.path?'active':''}" aria-pressed="${i===state.path}">${i===0?'推荐路径':`其他路径 ${i+1}`}</button>`).join('')}</div><div class="reading" id="path-content">${inline(q.教学路径[state.path])}</div><div class="path-label">优先使用推荐路径。其他入口可能用于解题或核验，不强凑三种独立算法。</div></section><section class="step"><h3 class="step-heading"><span class="step-number">03</span>凭什么可以停止</h3><div class="reading stop-box">${inline(q.停止条件)}</div></section><section class="step"><h3 class="step-heading"><span class="step-number">04</span>什么时候不能这样用</h3><div class="reading boundary">${inline(q.边界与迁移提醒)}</div><div class="answer-row"><span>AI首答 <b class="${q.首答!==q.机构参考?'wrong':''}">${esc(q.首答)}</b></span><span>机构参考 <b>${esc(q.机构参考)}</b></span>${q.首答!==q.机构参考?`<span>修订 <b>${esc(q.本轮工作答案)}</b></span>`:''}</div><div class="subtle">机构参考不等于官方赋分。首答保留，不因核验而覆盖。</div>${q.方法来源?`<details style="margin-top:17px"><summary>方法来源与借用边界</summary><div class="subtle">${inline(q.方法来源)}</div></details>`:''}</section>`;}
  function renderXingce(){const main=$('#main');main.innerHTML=banner('XINGCE / STUDY ONE QUESTION','对着一道题，学会一种判断。','先看读题信号，再执行最简路径。理解何时可以停止，也知道何时必须换方法。',bundle?'135 题讲解已就绪':'本机资料 · 由你掌握')+`<div class="quick-picks"><span>建议先读</span>${[[117,'资料 · 比较三条路径'],[118,'资料 · 一条就够'],[54,'言语 · 为什么改选'],[93,'定义 · 守住题内条件']].map(([n,t])=>`<button data-q="${n}" class="${state.q===n?'active':''}">${n} ${t}</button>`).join('')}</div>`+(!bundle?empty():`<div class="toolbar"><div class="search-box"><input id="question-search" type="search" placeholder="搜索题号、题型或读题关键词" value="${esc(state.search)}" aria-label="搜索题目"></div><select id="question-filter" aria-label="题目筛选"><option value="all">全部讲解</option><option value="recommended">建议先读的4题</option><option value="wrong">AI首答需修正的题</option><option value="saved">我收藏的题</option></select><span id="result-count" class="route-count"></span></div><div id="question-strip" class="question-strip" aria-label="题号目录"></div><div id="lesson"></div>`);
    if(!bundle)return;$('#question-filter').value=state.filter;strip();const q=allQuestions().find(q=>q.题号===state.q)||allQuestions()[116];$('#lesson').innerHTML=lesson(q);
    $('#question-search').oninput=e=>{state.search=e.target.value;strip();};$('#question-filter').onchange=e=>{state.filter=e.target.value;strip();};
    $('#question-note').oninput=()=>{records.notes['x'+state.q]=$('#question-note').value;$('#note-status').textContent='正在保存…';clearTimeout(noteTimer);noteTimer=setTimeout(()=>{$('#note-status')&&($('#note-status').textContent=saveRecords()?'已保存在当前浏览器':'未能保存，请导出备份');},350);};
    $('#save-note').onclick=()=>{records.notes['x'+state.q]=$('#question-note').value;if(saveRecords()){$('#note-status').textContent='已保存在当前浏览器';toast('笔记已保存');}};
    $('#bookmark').onclick=()=>{records.favorites=savedToggle(state.q);saveRecords();renderXingce();};$('#reveal-toggle').onclick=()=>{state.reveal=!state.reveal;renderXingce();};$('#prev-question').onclick=()=>neighbor(-1);$('#next-question').onclick=()=>neighbor(1);
  }
  function savedToggle(n){return records.favorites.includes(n)?records.favorites.filter(x=>x!==n):[...records.favorites,n];}
  function neighbor(d){let qs=filtered();let i=qs.findIndex(q=>q.题号===state.q);if(i<0){qs=allQuestions();i=qs.findIndex(q=>q.题号===state.q);}if(qs[i+d])go('xingce',qs[i+d].题号);else toast('已经到这一组的边界了');}
  const docCards=(docs)=>`<div class="card-grid">${docs.map(d=>`<button class="resource-card" data-doc="${d.id}"><div class="eyebrow">${esc(d.group)}</div><span class="arrow">↗</span><h2>${esc(d.title)}</h2><p>${esc(d.description||'按任务查阅，不必从头读完。')}</p></button>`).join('')}</div>`;
  function teachingExample(example,kind){
    if(!example)return '';
    const source=example.source_id&&(bundle?.crossYearExamples||[]).find(x=>x.source_id===example.source_id);
    return `<section class="teaching-example ${kind}"><h4>${esc(example.title)}</h4><ol>${example.steps.map(s=>`<li><span class="node-ref">节点 ${esc(s.node)}</span> ${esc(s.text)}</li>`).join('')}</ol>${source?`<a class="paper-link teaching-source-link" href="#/example/${esc(source.id)}">看这道示范的原题与逐题依据 →</a>`:example.authored?'<p class="subtle">自拟边界，用于检查适用条件，不计真题检验。</p>':''}</section>`;
  }
  function relationMap(t){
    if(t.relation_map!=='shared-endpoint')return '';
    return `<figure class="relation-map"><svg viewBox="0 0 460 245" role="img" aria-label="A和B分别指向同一个末值T，两个比值相除得到B除以A"><defs><marker id="shared-endpoint-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#315f51"/></marker></defs><path d="M95 158 L208 70" fill="none" stroke="#315f51" stroke-width="2" marker-end="url(#shared-endpoint-arrow)"/><path d="M365 158 L252 70" fill="none" stroke="#315f51" stroke-width="2" marker-end="url(#shared-endpoint-arrow)"/><path d="M145 185 H315" fill="none" stroke="#8b6b36" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#shared-endpoint-arrow)"/><rect x="160" y="18" width="140" height="48" rx="10" fill="#e5efe7"/><rect x="15" y="160" width="120" height="48" rx="10" fill="#f0f5ec"/><rect x="325" y="160" width="120" height="48" rx="10" fill="#f0f5ec"/><g fill="#254b42" font-size="16" text-anchor="middle"><text x="230" y="48">同一个末值 T</text><text x="75" y="189">基期 A</text><text x="385" y="189">基期 B</text><text x="112" y="105">T/A = u</text><text x="348" y="105">T/B = v</text><text x="230" y="232">目标 B/A = u/v</text></g></svg><figcaption>先确认两条箭头终点完全相同，再沿目标方向约分。</figcaption></figure>`;
  }
  function strategyTeaching(c){
    const t=c.teaching;if(!t)return '';
    return `<section class="strategy-teaching" aria-label="${esc(c.title)}的能力与决策流程"><h4>这条方法调用哪些能力</h4><ol class="ability-strip">${t.ability.map(a=>`<li>${esc(a)}</li>`).join('')}</ol>${relationMap(t)}<h4>拿到题，沿着问题走</h4><div class="decision-flow" role="group" aria-label="决策流程图">${t.flow.map(n=>`<section class="decision-node"><h5><span>${esc(n.id)}</span>${esc(n.question)}</h5><ul>${n.choices.map(ch=>`<li>${esc(ch.label)} <strong>→ ${esc(ch.to)}</strong></li>`).join('')}</ul></section>`).join('')}</div><p class="method-choice"><strong>为什么首选这条路：</strong>${esc(t.choice)}</p>${teachingExample(t.success,'success')}<details class="teaching-failure"><summary>看它在哪里容易失败或不能证明唯一</summary>${teachingExample(t.failure,'failure')}</details><p class="subtle">${esc(t.evidence_note)}</p>${(t.related_methods||[]).length?`<div class="quick-picks">${t.related_methods.map(id=>(PUBLIC.strategyCards||[]).find(m=>m.id===id)).filter(Boolean).map(m=>`<a class="paper-link" href="#/methods/${esc(m.category)}/${esc(m.id)}">关联方法：${esc(m.title)} →</a>`).join('')}</div>`:''}</section>`;
  }
  function practiceRecords(){if(!records.practice||typeof records.practice!=='object'||Array.isArray(records.practice))records.practice={};return records.practice;}
  function practiceStatus(v){const first=v.firstSubmission;return (first?`首次保存：${first.choice}；${first.hintSeen||first.reviewSeen?'已接触提示或核验':'保存前未打开提示或核验'}。`:'还没选答案；先选答案并填写用时。')+(v.hintSeen?' 已打开提示。':'')+(v.reviewSeen?' 已打开核验。':'');}
  function guidedPractice(c,p){
    return `<details class="strategy-practice guided-practice"><summary>先独立试用：${p.questions.length}题（答案单独展开）</summary><p>${esc(p.note)}</p>${p.questions.map((q,i)=>{
      const key=c.id+'|'+q.source_id,v=practiceRecords()[key]||{};
      return `<section class="practice-question" data-practice-branch="${esc(c.id)}" data-practice-source="${esc(q.source_id)}"><h4>${esc(q.label)}</h4>${q.image?`<img class="source-thumb" src="${esc(q.image)}" alt="${esc(q.label)}试用题面" loading="lazy" data-zoom data-zoom-title="${esc(q.label)} · 试用题面">`:`<div class="question-text practice-text">${esc(q.questionText)}</div>`}<fieldset><legend>我的独立作答</legend><label>选项<select class="practice-choice" aria-label="${esc(q.label)}选项"><option value="">未选择</option>${['A','B','C','D'].map(a=>`<option value="${a}" ${v.choice===a?'selected':''}>${a}</option>`).join('')}</select></label><label>用时（秒，自填）<input class="practice-seconds" type="number" min="0" step="1" value="${Number.isFinite(v.seconds)?v.seconds:''}" aria-label="${esc(q.label)}用时秒数"></label><label class="practice-seen-label"><input class="practice-seen" type="checkbox" ${v.seen?'checked':''}>这题以前做过／看过</label><label class="practice-difficulty-label">哪一步难执行？<textarea class="practice-difficulty" aria-label="${esc(q.label)}难执行步骤" placeholder="例如：不知道该比较哪两个量。">${esc(v.difficulty||'')}</textarea></label></fieldset><button class="soft" data-practice-save>保存这题的作答</button><p class="practice-status subtle" aria-live="polite">${esc(practiceStatus(v))}</p><details data-practice-reveal="hint"><summary>需要时看一个提示（会记录已打开）</summary><div class="practice-reveal-body"></div></details><details data-practice-reveal="review"><summary>完成后查看核验（会记录已打开）</summary><div class="practice-reveal-body"></div></details></section>`;
    }).join('')}<p class="subtle">只保存在当前浏览器，可随收藏与笔记导出。记录是否点开提示，不推断你在其他地方是否见过答案。</p></details>`;
  }
  function savePractice(section,exposure){
    const branch=section.dataset.practiceBranch,sid=section.dataset.practiceSource,key=branch+'|'+sid,old=practiceRecords()[key]||{},choice=$('.practice-choice',section).value,raw=$('.practice-seconds',section).value,seconds=raw!==''?Number(raw):null;
    const value={...old,source_id:sid,method_id:branch,choice,seconds:Number.isFinite(seconds)&&seconds>=0?seconds:null,seen:$('.practice-seen',section).checked,difficulty:$('.practice-difficulty',section).value,updatedAt:new Date().toISOString()};
    if(choice&&!old.firstSubmission)value.firstSubmission={choice,seconds:value.seconds,seen:value.seen,hintSeen:!!old.hintSeen,reviewSeen:!!old.reviewSeen,at:value.updatedAt};
    if(exposure)value[exposure==='hint'?'hintSeen':'reviewSeen']=true;
    practiceRecords()[key]=value;const ok=saveRecords();$('.practice-status',section).textContent=(ok?'已保存。':'本次未能保存。')+practiceStatus(value);return value;
  }
  document.addEventListener('click',e=>{const button=e.target.closest('[data-practice-save]');if(button)savePractice(button.closest('.practice-question'));});
  document.addEventListener('toggle',e=>{
    const detail=e.target;if(!detail.matches?.('[data-practice-reveal]')||!detail.open)return;
    const section=detail.closest('.practice-question'),branch=section.dataset.practiceBranch,sid=section.dataset.practiceSource,kind=detail.dataset.practiceReveal;
    savePractice(section,kind);const body=$('.practice-reveal-body',detail);
    if(kind==='hint'){const q=bundle?.strategyPractice?.[branch]?.questions.find(q=>q.source_id===sid);body.textContent=q?.hint||'先核题目问什么，再选方法。';}
    else{const v=bundle?.strategyPracticeReview?.[branch]?.[sid];body.innerHTML=v?`<p>核验答案：<strong>${esc(v.answer)}</strong></p><p>${esc(v.execution)}</p>${v.kind==='self-authored'?'<p class="subtle">助手自拟迁移题，用于检验规则边界，不计真题覆盖。</p>':`<a class="paper-link" href="#/example/${esc(v.review_id)}">查看原首答与核验范围 →</a>`}`:'<p>本题核验尚未接入。</p>';}
  },true);
  function strategyPractice(c){
    const p=bundle?.strategyPractice?.[c.id];if(!p||!Array.isArray(p.questions))return '';
    if(p.mode==='guided-transfer/v1')return guidedPractice(c,p);
    const qs=p.questions.filter(q=>practiceImage(q.image));
    return `<details class="strategy-practice"><summary>先独立试用：${qs.length}题（不含答案）</summary><p>${esc(p.note)}</p>${qs.map(q=>`<section><h4>${esc(q.label)}</h4><img class="source-thumb" src="${esc(q.image)}" alt="${esc(q.label)}原题" loading="lazy" data-zoom data-zoom-title="${esc(q.label)}"><p class="subtle">记录：选项、用时、是否需要提示；做过的题另标。</p></section>`).join('')}</details>`;
  }
    function examplesFor(category){
    const reviewed=(bundle?.crossYearExamples||[]).filter(x=>x.category===category);
    const covered=new Set(reviewed.flatMap(x=>(x.methods||[]).map(m=>m.id)));
    const notes=(PUBLIC.crossYearNotes||[]).filter(x=>x.category===category&&!(x.methods||[]).every(m=>covered.has(m.id)));
    return [...reviewed,...notes];
  }
  function exampleCountLabel(items){
    const reviewed=items.filter(x=>x.kind==='review').length,notes=items.length-reviewed;
    return [reviewed?`${reviewed}个逐题来源位置`:'',notes?`${notes}段待专项检验讲解`:''].filter(Boolean).join('＋');
  }
  function categoryCoverage(c){
    if(c.paused)return '暂缓专项';
    const a=examplesFor(c.id);if(!a.length)return '仅2026同卷示范 · 跨年待整理';
    return exampleCountLabel(a);
  }
  function researchScopeNote(items){
    const cutoff=PUBLIC.researchScope?.minimum_year_inclusive;
    if(!Number.isInteger(cutoff))return '';
    const reviewed=items.filter(x=>x.kind==='review'),current=reviewed.filter(x=>x.year>=cutoff).length,older=reviewed.length-current;
    return `<p class="subtle">后续未分析题只推进${cutoff}年（含）及以后；早期成果保留。${reviewed.length?`本类已检验来源：当前年份范围${current}个，早期保留${older}个；包含争议和跨卷同题，不等于独立题数。`:''}</p>`;
  }
  function branchExamples(c){
    const a=(PUBLIC.methods||[]).flatMap(category=>examplesFor(category.id)).filter(x=>(x.methods||[]).some(m=>m.id===c.id));
    if(!a.length)return '';
    const years=[...new Set(a.flatMap(x=>x.years||[x.year]))].filter(Number.isFinite).sort((a,b)=>a-b),ordered=mixedYears(a);
    const card=x=>`<a class="cross-year-card" href="#/example/${esc(x.id)}"><strong>${esc(x.title)}</strong><span>${esc(x.status)} · 看原题与依据 →</span></a>`;
    return `<section class="branch-cross-year" aria-label="这条方法的跨年题例"><h4>这条方法怎样用在其他年份？</h4><p class="subtle">${exampleCountLabel(a)} · ${years[0]}—${years[years.length-1]}年。先对照下面的不同年份；同题跨卷及争议均保留。</p><div class="cross-year-grid">${ordered.slice(0,3).map(card).join('')}</div>${ordered.length>3?`<details class="branch-example-more"><summary>查看其余${ordered.length-3}条题例（${years.join('、')}年）</summary><div class="cross-year-grid">${ordered.slice(3).map(card).join('')}</div></details>`:''}</section>`;
  }
  function taskMap(c){
    if(!c.taskMap)return '';
    return `<section class="task-map" aria-label="${esc(c.title)}任务分流图"><h3>先判断题目让你做什么</h3><p class="subtle">按设问选一个动作。相关方法可以组合使用；遇到文字推断或自定规则，进入对应方法。</p><div class="task-map-grid">${c.taskMap.map(t=>`<div class="task-map-group"><p>${esc(t.signal)}</p>${(t.targets||[t]).map(target=>`<a href="#/methods/${esc(target.category||c.id)}/${esc(target.branch)}"><strong>↓ ${esc(target.label)}</strong></a>`).join('')}</div>`).join('')}</div></section>`;
  }
  function crossYearEntry(c){
    const a=examplesFor(c.id);if(!a.length)return '';
    const years=[...new Set(a.flatMap(x=>x.years||[x.year]))].filter(Number.isFinite).sort((a,b)=>a-b);
    return `<aside class="cross-year-entry"><strong>本类不只2026：${years[0]}—${years[years.length-1]}年</strong><p>${exampleCountLabel(a)}，不代表整类全量完成。每张方法卡下直接列出跨年题例，也可按年份查整类题例库。</p>${researchScopeNote(a)}<button class="soft" data-example-library>按年份找本类题例 ↓</button></aside>`;
  }
  function mixedYears(items){
    const groups=new Map();for(const x of items){if(!groups.has(x.year))groups.set(x.year,[]);groups.get(x.year).push(x);}
    const years=[...groups.keys()].sort((a,b)=>b-a),out=[];
    // Give different years a visible place before adding the next item from a year.
    while(years.some(y=>groups.get(y).length))for(const y of years){const x=groups.get(y).shift();if(x)out.push(x);}
    return out;
  }
  function methodExamples(c){
    if(c.paused)return '<p class="subtle">本类按当前取舍暂缓专项训练。</p>';
    const all=examplesFor(c.id);
    if(state.exampleCategory!==c.id){state.exampleCategory=c.id;state.exampleYear='all';state.exampleStatus='all';state.exampleLimit=12;}
    if(!all.length)return '<section class="cross-year-library"><h3>跨年题例</h3><p>本类跨年示范尚未整理到可展示状态。目前只有下方的2026同卷示范，不代表整类已完成。</p></section>';
    const years=[...new Set(all.flatMap(x=>x.years||[x.year]))].sort((a,b)=>b-a);
    const filtered=all.filter(x=>(state.exampleYear==='all'||(x.years||[x.year]).includes(Number(state.exampleYear)))&&(state.exampleStatus==='all'||x.status===state.exampleStatus));
    const shown=mixedYears(filtered).slice(0,state.exampleLimit),reviewed=all[0].kind==='review';
    return `<section class="cross-year-library" id="cross-year-library" aria-label="跨年题例库"><h3>跨年题例 · ${exampleCountLabel(all)}</h3><p>${reviewed?'逐题来源与旧讲解分别标记，包含跨卷同题和争议。旧讲解不代表已完成当前版本专项检验；点击一道题查看对应依据。':'这些是已有方法卡中的跨年讲解片段；本类尚未完成全量逐题策略检验。'}</p><div class="example-filters"><label>年份<select id="example-year" aria-label="年份"><option value="all">全部年份</option>${years.map(y=>`<option value="${y}" ${state.exampleYear==y?'selected':''}>${y}年</option>`).join('')}</select></label>${reviewed?`<label>核验状态<select id="example-status" aria-label="核验状态"><option value="all">全部状态</option>${['已有策略检验','存在争议'].map(s=>`<option ${state.exampleStatus===s?'selected':''}>${s}</option>`).join('')}</select></label>`:''}<span class="subtle">显示${shown.length} / ${filtered.length}</span></div><div class="cross-year-grid">${shown.map(x=>`<a class="cross-year-card" href="#/example/${esc(x.id)}"><span class="example-status ${x.status==='存在争议'?'disputed':''}">${esc(x.status)}</span><strong>${esc(x.title)}</strong><span>${esc(x.task||((PUBLIC.strategyCards||[]).find(m=>m.id===x.methods[0]?.id)?.title)||'分类方法示范')}</span><span class="example-enter">看原题与解法 →</span></a>`).join('')}</div>${shown.length<filtered.length?'<button class="soft" data-more-examples>再显示12条</button>':''}${!shown.length?'<p>这个筛选条件下没有已整理记录。</p>':''}<p class="subtle">选不同年份比较同一动作。题例数量不等于独立新题次数，也不代表你已掌握。</p></section>`;
  }
  let pdfLibrary;
  async function renderPdfOriginals(container,paper,pages,title){
    let documentTask;
    try{
      pdfLibrary ||= import('./vendor/pdfjs/pdf.min.mjs');
      const library=await pdfLibrary;
      library.GlobalWorkerOptions.workerSrc=new URL('vendor/pdfjs/pdf.worker.min.mjs',location.href).href;
      documentTask=library.getDocument({url:paper,cMapUrl:'vendor/pdfjs/cmaps/',cMapPacked:true,standardFontDataUrl:'vendor/pdfjs/standard_fonts/',wasmUrl:'vendor/pdfjs/wasm/'});
      const pdf=await documentTask.promise;
      for(const number of pages){
        if(!container.isConnected)break;
        const page=await pdf.getPage(number),base=page.getViewport({scale:1}),viewport=page.getViewport({scale:2000/Math.max(base.width,base.height)});
        const canvas=document.createElement('canvas');canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
        await page.render({canvasContext:canvas.getContext('2d'),viewport}).promise;
        if(!container.isConnected)break;
        const image=document.createElement('img');image.className='source-thumb';image.alt=title+'所在原卷第'+number+'页';image.src=canvas.toDataURL('image/png');image.dataset.zoom='';image.dataset.zoomTitle=image.alt;
        const section=document.createElement('details');section.className='cross-original-page';section.open=number===pages[0];
        const heading=document.createElement('summary');heading.textContent='原卷第'+number+'页 · 点图放大';section.append(heading,image);container.append(section);
      }
      if(container.isConnected)container.querySelector('[role="status"]')?.remove();
    }catch{
      if(container.isConnected)container.querySelector('[role="status"]').textContent='原页暂未显示，请用下方原卷链接打开；方法与核验仍可阅读。';
    }finally{if(documentTask)await documentTask.destroy();}
  }
  function renderExample(id){
    const x=[...(bundle?.crossYearExamples||[]),...(PUBLIC.crossYearNotes||[])].find(x=>x.id===id);
    if(!x){$('#main').innerHTML='<h1>题例尚未载入</h1><p>请回到分类方法选择已有题例。</p><button data-view="methods">返回分类方法</button>';return;}
    const c=(PUBLIC.methods||[]).find(c=>c.id===x.category),methods=(x.methods||[]).map(m=>(PUBLIC.strategyCards||[]).find(c=>c.id===m.id)).filter(Boolean);
    let original='';
    if(x.kind==='review'&&/^cross-year-papers\/[a-f0-9]{16}\.pdf$/.test(x.paper||'')){
      const pages=(x.pages||[]).filter(n=>Number.isInteger(n)&&n>0);
      original=`<section class="example-original"><h2>先看原题与材料</h2><p>按题号找到本题；原页保留选项、图表与共享材料，点图可放大。</p>${(x.pageImages||[]).filter(p=>/^cross-year-pages\/[a-f0-9]{16}-[0-9]+\.jpg$/.test(p.image)).map(p=>`<details class="cross-original-page" ${p.page===pages[0]?'open':''}><summary>原卷第${p.page}页 · 点图放大</summary><img class="source-thumb" src="${esc(p.image)}" alt="${esc(x.title)}所在原卷第${p.page}页" loading="lazy" data-zoom data-zoom-title="${esc(x.title)} · 原卷第${p.page}页"></details>`).join('')}<p class="subtle">需要整卷上下文时，也可打开PDF：</p><div class="quick-picks">${(pages.length?pages:[null]).map(p=>`<a class="paper-link" href="${esc(x.paper)}${p?'#page='+p:''}" target="_blank" rel="noopener noreferrer">${p?'原卷第'+p+'页':'打开原卷'} ↗</a>`).join('')}</div></section>`;
      if(x.originalMode==='pdf'&&pages.length){
        original=`<section class="example-original"><h2>先看原题与材料</h2><p>以下直接读取原PDF并显示对应页，请按题号定位；点图可放大。</p><div class="original-pdf-pages"><p role="status">正在读取原页…</p></div><p>需要完整上下文时，打开对应原卷：</p><div class="quick-picks">${pages.map(p=>`<a class="paper-link" href="${esc(x.paper)}#page=${p}" target="_blank" rel="noopener noreferrer">原卷第${p}页 ↗</a>`).join('')}</div></section>`;
      }
    }else{
      const evidence=bundle?.strategyEvidence||(bundle?window.STUDY_STRATEGY_EVIDENCE:null),ids=[...new Set(methods.flatMap(m=>evidence?.cases?.[m.id]||[]))],pages=ids.map(k=>evidence?.pages?.[k]).filter(p=>p&&(x.years||[x.year]).some(y=>p.label.startsWith(String(y))));
      if(pages.length)original=`<details><summary>同方法、同年份的已关联原页（按卷别题号核对）</summary>${pages.map(p=>`<p>${esc(p.label)}</p><img class="source-thumb" src="${esc(p.image)}" alt="${esc(p.label)}" loading="lazy" data-zoom data-zoom-title="${esc(p.label)}">`).join('')}</details>`;
      else original='<p class="subtle">此讲解片段的精确原页尚未关联，当前先展示已有讲解与方法入口。</p>';
    }
    $('#main').innerHTML=`<button class="doc-back" data-method="${esc(x.category)}">← 返回${esc(c?.title||'分类方法')}跨年题例</button><article class="panel method-guide cross-year-lesson"><div class="eyebrow">${esc(x.status)}</div><h1>${esc(x.title)}</h1>${x.task?`<p class="method-aim">${esc(x.task)}</p>`:''}${original}<h2>这道题怎样执行方法</h2><div class="example-execution">${inline(x.execution)}</div><h3>对应的分类方法</h3><div class="quick-picks">${methods.map(m=>`<a class="paper-link" href="#/methods/${esc(m.category)}/${esc(m.id)}">${esc(m.title)} →</a>`).join('')}</div>${x.issues?.length?`<details ${x.status==='存在争议'?'open':''}><summary>条件、错误与争议</summary><ul>${x.issues.map(s=>`<li>${esc(s)}</li>`).join('')}</ul></details>`:''}${x.kind==='review'?`<details><summary>查看首答与核验范围</summary><p>原首答：${esc(x.first==null?'来源尚未完整关联，保留缺口':typeof x.first==='string'?x.first:JSON.stringify(x.first))}；机构参考：${esc(typeof x.reference==='string'?x.reference:'见原核验记录')}。</p><p>${esc(x.result)}</p><p>${esc(x.exposure)}</p><p class="subtle">保留首答与接触情况；答案字母一致不等于依据正确，也不等于用户独立掌握。</p></details>`:'<p class="subtle">这是已有讲解片段，不能当作本类别全量检验完成。</p>'}</article>`;
    if(x.originalMode==='pdf')renderPdfOriginals($('.original-pdf-pages'),x.paper,x.pages,x.title);
    window.scrollTo(0,0);
  }

  function strategyCards(category){
    const cards=(PUBLIC.strategyCards||[]).filter(c=>c.category===category);if(!cards.length)return '';
    return `<section class="strategy-branches"><h3>题目长这样时，换一个执行分支</h3><p class="subtle">先选符合题干的一张。各分支的流程、跨年题例和试用入口分别列出；逐题处理不等于教学与个人迁移均已完成。</p>${cards.map(c=>{
      const evidence=bundle?.strategyEvidence||(bundle?window.STUDY_STRATEGY_EVIDENCE:null),ids=evidence?.cases?.[c.id]||[];
      const pages=ids.map(id=>evidence.pages?.[id]).filter(p=>p&&typeof p.label==='string'&&typeof p.image==='string'&&(/^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(p.image)||/^strategy-pages\/[a-f0-9]{24}\.jpg$/.test(p.image)));
      const worked=(c.worked||'').split(/\n\s*\n/).filter(Boolean);
      const examples=worked.map((p,i)=>i===0&&!c.teaching?`<div class="stop-box"><p>${inline(p)}</p></div>`:`<details class="strategy-example"><summary>${esc(p.match(/^(?:(?:失败例|失败修订|跨年)?20\d{2}[^：]{0,32}|分歧保留|自拟边界|自拟反例|外部参考|外部核查边界)(?=：)/)?.[0]||('补充示范 '+i))} · 展开示范</summary><p>${inline(p)}</p></details>`).join('');
      return `<details class="strategy-card" id="branch-${esc(c.id)}" ${route().branch===c.id?'open':''}><summary>${esc(c.title)}</summary><p class="subtle">${esc(c.status)}</p><h4>什么时候用</h4><p>${esc(c.signal)}</p>${strategyTeaching(c)}${branchExamples(c)}${strategyPractice(c)}${c.teaching?'<details class="teaching-short"><summary>短步骤与停止条件</summary>':''}${c.steps.map((s,i)=>`<div class="strategy-action"><b>${i+1}. ${esc(s.action)}</b><p class="method-why">为什么：${esc(s.why)}</p></div>`).join('')}<h4>做到哪里停</h4><p>${esc(c.stop)}</p>${c.teaching?'</details><details><summary>更多示范与历史核验</summary>':''}<h4>对着例子看</h4><p>${esc(c.example)}</p>${examples}${c.teaching?'</details>':''}${pages.length?`<details class="strategy-source"><summary>对照真题原页（点图可放大）</summary>${pages.map(p=>`<p class="source-caption">${esc(p.label)}</p><img class="source-thumb" src="${esc(p.image)}" alt="${esc(p.label)}" loading="lazy" data-zoom data-zoom-title="${esc(p.label)}">`).join('')}</details>`:(examplesFor(category).some(x=>x.kind==='review'&&(x.methods||[]).some(m=>m.id===c.id))?'<p class="subtle">原题与核验范围可从上方“这条方法的跨年题例”进入。</p>':'<p class="subtle">本卡尚未接入可展示原页；题源与阅读范围见下方检验状态。</p>')}<h4>什么时候失效</h4><p>${esc(c.boundary)}</p><details><summary>题源与检验状态</summary><p>${c.sources.map(esc).join('<br>')}</p><p>${esc(c.check)}</p><a href="#/methods/${esc(category)}/${esc(c.id)}">定位到这张方法卡 ↗</a></details></details>`;
    }).join('')}</section>`;
  }
  function renderMethods(){
    const entries=PUBLIC.methods||[],chosen=entries.find(c=>c.id===route().id);
    let html=banner('分类方法 / 从单题走向可重复的判断','先学一类的方法，再看它怎样用于一道题。','每类按钮标明实际整理程度。跨年题例优先展示；2026整卷保留为另一条阅读入口。');
    html+=`<div class="method-picker" aria-label="十一类方法目录">${entries.map(c=>`<button class="${chosen?.id===c.id?'active':''}" data-method="${c.id}">${esc(c.title)}<small>${esc(categoryCoverage(c))}</small></button>`).join('')}</div>`;
    if(!chosen){html+=`<section class="panel method-guide"><h2>从这里开始</h2><p>选择上面一个类别，每次只读一套流程。</p><p>先理解“为什么这样做”，再打开例题看具体应用。其他路径留到首选方法学懂之后。</p><button class="primary" data-method="data">先看资料分析：把公式讲成人话 →</button><p class="subtle">这里是可核查的教学策略，不是模型内部思考记录。通用不等于所有题目都套同一个公式。</p></section>`;}
    else{const c=chosen;html+=`<article class="panel method-guide"><div class="eyebrow">${esc(categoryCoverage(c))}</div><h2>${esc(c.title)}</h2><p class="method-aim">${esc(c.aim)}</p>${crossYearEntry(c)}${taskMap(c)}${strategyCards(c.id)}${methodExamples(c)}${c.taskMap?'<details class="method-extra"><summary>查阅整类通用步骤</summary>':''}<h3>拿到题，先看哪里？</h3><p>${esc(c.read)}</p>${c.steps.map((s,i)=>`<section class="method-action"><div class="step-number">${i+1}</div><div><h3>${esc(s[0])}</h3><p>${esc(s[1])}</p><p class="method-why">为什么：${esc(s[2])}</p></div></section>`).join('')}<section class="stop-box"><h3>做到哪里可以停？</h3><p>${esc(c.stop)}</p></section><h3>用一个小例子理解</h3><p>${esc(c.example)}</p><details><summary>这一类还要怎样细分？</summary><ul>${c.branches.map(t=>`<li>${esc(t)}</li>`).join('')}</ul></details><details><summary>什么时候不能这样用？</summary><p>${esc(c.boundary)}</p></details>${c.taskMap?'</details>':''}<details class="same-paper-examples"><summary>另看2026副省级同卷示范</summary><div class="quick-picks">${c.questions.map(n=>`<button data-q="${n}" data-method-example>第 ${n} 题 →</button>`).join('')}</div></details>${c.source?`<details><summary>已读方法来源与借用范围</summary><p><a href="${esc(safeURL(c.source.url)||'#')}" target="_blank" rel="noopener noreferrer">${esc(c.source.title)} ↗</a></p><p>${esc(c.source.use)}</p></details>`:''}<p class="subtle">同卷例题用于示范；自拟例子用于理解。两者都不能证明你已经能独立迁移。本轮新增的整类流程也不继承原四张卡的跨卷验证结论。</p></article>`;}
    html+=`<details class="method-extra"><summary>查阅原有方法卡、读题地图与验证记录</summary>${docCards(PUBLIC.docs.filter(d=>d.group==='行测方法'||d.group==='学习起点'))}</details>`;$('#main').innerHTML=html;if(route().branch)document.getElementById('branch-'+route().branch)?.scrollIntoView({block:'start'});
  }
  function renderLibrary(){const groups=[...new Set(PUBLIC.docs.map(d=>d.group))];$('#main').innerHTML=banner('LIBRARY / READ WITH A PURPOSE','资料已经分类，按问题取用。','把长文拆成能导航的阅读页。研究记录、政策和教学方法分开，不要求全部背完。')+groups.map(g=>`<h2 class="library-heading">${esc(g)}</h2>`+docCards(PUBLIC.docs.filter(d=>d.group===g))).join('');}
  function renderDoc(id){const d=PUBLIC.docs.find(x=>x.id===id);if(!d){$('#main').innerHTML=banner('LIBRARY','这份内容尚未收录。','可返回资料架选择已有文档。')+`<button class="primary" data-view="library">返回资料架</button>`;return;}const titles=[...d.content.matchAll(/^(#{1,4})\s+(.+)$/gm)];$('#main').innerHTML=`<button class="doc-back" data-view="${d.group==='行测方法'||d.group==='学习起点'?'methods':'library'}">← 返回${d.group==='行测方法'||d.group==='学习起点'?'方法卡':'资料架'}</button><div class="doc-layout"><article class="article markdown">${markdown(d.content,d)}</article><nav class="doc-toc" aria-label="本文目录"><div class="eyebrow">本文目录</div>${titles.filter(t=>t[1].length<=2).map(t=>`<a href="#heading-${titles.indexOf(t)}" data-heading="heading-${titles.indexOf(t)}">${esc(t[2])}</a>`).join('')}</nav></div>`;}
  function renderShenlun(){const titles=['管理做法概括','传统工艺取舍','指定标题短评','问题与针对性建议','关系主题作文'];let html=banner('SHENLUN / FROM MATERIAL TO ARGUMENT','看清材料，才知道怎么组织。','先看任务和证据怎样形成观点，再读完整示范。这里不提供虚构的官方评分。');if(!bundle){$('#main').innerHTML=html+empty()+docCards(PUBLIC.docs.filter(d=>d.group==='申论方法'));return;}
    const n=Math.max(1,Math.min(5,state.shenlun)),q=bundle.shenlun[n-1],mapping=bundle.shenlunSections?.[n]||'';
    html+=`<div class="shenlun-tabs">${titles.map((t,i)=>`<button data-shenlun="${i+1}" class="${n===i+1?'active':''}">第${i+1}题 ${t}</button>`).join('')}</div><div class="lesson-head"><div><div class="lesson-tag">2026 副省级申论 · 冻结首答</div><h2>${titles[n-1]}</h2></div><span class="status-chip">${q['含标点非空白字数']} 字 · 非官方评分</span></div><section class="panel"><div class="panel-bar"><strong>先看材料怎样变成写法</strong><span>依据与组织选择</span></div><div class="article markdown" style="border:0;border-radius:0">${markdown(mapping)}</div></section><section class="panel" style="margin-top:20px"><div class="panel-bar"><strong>完整首答示范</strong><span>与核验后改进稿分开</span></div><div class="article reading shenlun-answer" style="border:0;border-radius:0">${esc(q.首答)}</div></section><div class="card-grid"><button class="resource-card" data-private-doc="shenlunReview"><div class="eyebrow">核验</div><h2>看五题核验与改进依据 ↗</h2><p>既检查AI，也检查参考的强断言与材料边界。</p></button><button class="resource-card" data-private-doc="shenlunRevisions"><div class="eyebrow">改进稿</div><h2>看另存的修订版本 ↗</h2><p>原首答没有被覆盖，比较改变了哪一个动作。</p></button></div>`;$('#main').innerHTML=html;
  }
  function render(){const r=route();if(r.view==='xingce'&&r.id){state.q=Math.min(135,Math.max(1,parseInt(r.id)||117));state.path=0;}
    document.querySelectorAll('.main-nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===r.view||(r.view==='doc'&&b.dataset.view==='library'||r.view==='example'&&b.dataset.view==='methods')));$('#module-section').hidden=r.view!=='xingce';$('#top-title').textContent=({xingce:'行测逐题研习',methods:'分类通用解题方法',shenlun:'申论写作工坊',library:'资料与研究书架',doc:'阅读资料',example:'跨年题例与方法'})[r.view]||'解题研习室';
    $('#data-state').textContent=bundle?($('#study-bundle')?'135题已预装 · 无需导入':'135题已载入当前浏览器'):'在线界面 · 待导入本机资料';moduleMenu();setFont();if(r.view==='example')renderExample(r.id);else if(r.view==='methods')renderMethods();else if(r.view==='library')renderLibrary();else if(r.view==='doc')renderDoc(r.id);else if(r.view==='shenlun')renderShenlun();else renderXingce();
  }
  function openImage(src,title){let valid=/^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(src);if(!valid){try{const u=new URL(src,location.href);valid=u.origin===location.origin&&['http:','https:','file:'].includes(u.protocol)&&(/(?:\/cross-year-pages\/[a-f0-9]{16}-[0-9]+|\/(?:strategy-pages|paper-images)\/[a-f0-9]{24})\.jpg$/.test(u.pathname)||/\/practice-images\/[a-f0-9]{24}\.(jpg|png|webp)$/.test(u.pathname));}catch{}}if(!valid)return;$('#large-image').src=src;$('#image-title').textContent=title;$('#image-dialog').showModal();}
  document.addEventListener('click',e=>{const b=e.target.closest('button,a,img');if(!b)return;if(b.hasAttribute('data-example-library')){$('#cross-year-library')?.scrollIntoView({block:'start'});}else if(b.hasAttribute('data-more-examples')){state.exampleLimit+=12;renderMethods();$('#cross-year-library')?.scrollIntoView({block:'start'});}else if(b.dataset.method){e.preventDefault();go('methods',b.dataset.method);window.scrollTo(0,0);}else if(b.dataset.view){e.preventDefault();go(b.dataset.view,b.dataset.view==='xingce'?state.q:null);}else if(b.dataset.q){if(!bundle){toast('请先导入本机学习资料包');return;}state.path=0;if(b.closest('.quick-picks')){state.module='全部模块';state.search='';state.filter='all';}go('xingce',b.dataset.q);}else if(b.dataset.module){state.module=b.dataset.module;state.search='';const qs=filtered();if(qs.length)state.q=qs[0].题号;go('xingce',state.q);}else if(b.dataset.path!==undefined){state.path=Number(b.dataset.path);const q=allQuestions().find(q=>q.题号===state.q);document.querySelectorAll('[data-path]').forEach(x=>{x.classList.toggle('active',x.dataset.path===b.dataset.path);x.setAttribute('aria-pressed',x.dataset.path===b.dataset.path);});$('#path-content').innerHTML=inline(q.教学路径[state.path]);}else if(b.hasAttribute('data-reveal')){state.reveal=true;renderXingce();}else if(b.dataset.doc){go('doc',b.dataset.doc);window.scrollTo(0,0);}else if(b.dataset.heading){e.preventDefault();$('#'+b.dataset.heading)?.scrollIntoView({behavior:'smooth',block:'start'});}else if(b.hasAttribute('data-import')){$('#bundle-input').click();}else if(b.hasAttribute('data-zoom')){openImage(b.src,b.dataset.zoomTitle||'第 '+state.q+' 题 · 原卷图');}else if(b.dataset.fullPage&&bundle){openImage(bundle.paper.pages[+b.dataset.fullPage-1],'原卷第 '+b.dataset.fullPage+' 页');}else if(b.dataset.shenlun){state.shenlun=+b.dataset.shenlun;renderShenlun();}else if(b.dataset.privateDoc&&bundle){$('#main').innerHTML=`<button class="doc-back" data-view="shenlun">← 返回申论工坊</button><article class="article markdown" style="margin-top:20px">${markdown(bundle[b.dataset.privateDoc]||'')}</article>`;window.scrollTo(0,0);}});
  document.addEventListener('change',e=>{if(e.target.id==='example-year'||e.target.id==='example-status'){state[e.target.id==='example-year'?'exampleYear':'exampleStatus']=e.target.value;state.exampleLimit=12;renderMethods();$('#cross-year-library')?.scrollIntoView({block:'start'});}});
  $('#import-button').onclick=()=>$('#bundle-input').click();$('#bundle-input').onchange=async e=>{const f=e.target.files[0];if(!f)return;try{if(f.size>100*1024*1024)throw Error('资料包超过100MB，请使用项目生成的资料包。');const o=validateBundle(JSON.parse(await f.text()));bundle=o;try{await cachedBundle(o);toast('资料已载入，并保存在当前浏览器。');}catch{toast('资料已载入，本次未能缓存；下次需重新导入。');}render();}catch(err){toast('导入失败：'+err.message);}finally{e.target.value='';}};
  $('#export-notes').onclick=()=>{const b=new Blob([JSON.stringify({schema:'gongkao-notes/v1',exportedAt:new Date().toISOString(),favorites:records.favorites,notes:records.notes,practice:practiceRecords()},null,2)],{type:'application/json'});const u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download='我的研习笔记.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);toast('已导出收藏与笔记；未包含原题。');};
  $('#font-smaller').onclick=()=>{records.font=Math.max(16,records.font-1);setFont();saveRecords();};$('#font-larger').onclick=()=>{records.font=Math.min(24,records.font+1);setFont();saveRecords();};$('#menu-button').onclick=()=>{const open=$('#sidebar').classList.toggle('open');$('#menu-button').setAttribute('aria-expanded',String(open));};$('#close-image').onclick=()=>$('#image-dialog').close();$('#image-dialog').onclick=e=>{if(e.target===$('#image-dialog'))$('#image-dialog').close();};
  window.addEventListener('hashchange',render);document.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)||e.target.isContentEditable||$('#image-dialog').open)return;if(route().view==='xingce'&&bundle&&['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();neighbor(e.key==='ArrowLeft'?-1:1);}});
  async function init(){try{const embedded=$('#study-bundle');if(embedded)bundle=validateBundle(JSON.parse(embedded.textContent));else{const old=await cachedBundle();if(old)bundle=validateBundle(old);}}catch{toast('本机资料未载入；可重新导入学习资料包。');}render();}init();
})();
