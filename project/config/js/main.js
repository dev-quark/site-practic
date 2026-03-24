class ConfiguratorApp {
    constructor() {
        this.dbData = {};
        this.selection = {};
        this.validator = null;
        this.searchTimeouts = {};
        this.activeFilters = {};
        this.activeCategoryFilter = 'motherboard'; // Активная категория в фильтре
        
        this.multiSelectCategories = ['ram', 'storage'];
        
        this.categories = [
            {id: 'motherboard', label: 'Материнская плата', dataKey: 'motherboard', multiSelect: false, icon: '🔌'},
            {id: 'cpu', label: 'CPU', dataKey: 'cpu', multiSelect: false, icon: '🖥️'},
            {id: 'ram', label: 'RAM', dataKey: 'ram', multiSelect: true, icon: '💾'},
            {id: 'gpu', label: 'GPU', dataKey: 'graphicsCard', multiSelect: false, icon: '🎮'},
            {id: 'storage', label: 'Накопитель', dataKey: 'storage', multiSelect: true, icon: '💿'},
            {id: 'cooler', label: 'Охлаждение', dataKey: 'cooler', multiSelect: false, icon: '❄️'},
            {id: 'psua', label: 'Блок питания', dataKey: 'powerSupply', multiSelect: false, icon: '⚡'},
            {id: 'case', label: 'Корпус', dataKey: 'case', multiSelect: false, icon: '📦'}
        ];

        this.init();
    }
    
    async init() {
        try {
            this.dbData = await dbLoader.loadAll();
            this.validator = new CompatibilityValidator(this.dbData);
            
            this.initializeFilters();
            this.renderSidebar();
            this.renderAllSections();
            this.setupEventListeners();
            
            console.log('✅ Конфигуратор успешно загружен');
        } catch (error) {
            console.error('❌ Ошибка инициализации:', error);
            alert('Ошибка загрузки базы: ' + error.message);
        }
    }

    initializeFilters() {
        this.categories.forEach(cat => {
            this.activeFilters[cat.id] = {
                search: '',
                brand: '',
                priceMin: '',
                priceMax: '',
                type: '',
                additional: {}
            };
        });
    }

    // 🎨 Рендер боковой панели с фильтрами
    renderSidebar() {
        const sidebar = document.getElementById('filterSidebar');
        if (!sidebar) return;
        
        let html = `
            <div class="sidebar-header">
                <h3>🔍 Фильтры</h3>
                <button class="close-sidebar-btn" id="closeSidebar">✕</button>
            </div>
            
            <nav class="filter-nav">
                ${this.categories.map(cat => `
                    <button class="filter-nav-item ${cat.id === this.activeCategoryFilter ? 'active' : ''}" 
                            data-category="${cat.id}">
                        <span class="nav-icon">${cat.icon}</span>
                        <span class="nav-label">${cat.label}</span>
                        <span class="nav-count" data-category="${cat.id}">0</span>
                    </button>
                `).join('')}
            </nav>
            
            <div class="filter-content">
                ${this.categories.map(cat => `
                    <div class="filter-panel ${cat.id === this.activeCategoryFilter ? 'active' : ''}" 
                         data-category="${cat.id}" 
                         id="filterPanel-${cat.id}">
                        ${this.renderFilterPanelContent(cat.id)}
                    </div>
                `).join('')}
            </div>
            
            <div class="sidebar-footer">
                <button class="reset-all-filters-btn" id="resetAllFilters">
                    🔄 Сбросить все фильтры
                </button>
            </div>
        `;
        
        sidebar.innerHTML = html;
    }

    // 🎨 Контент панели фильтров для категории
    renderFilterPanelContent(categoryId) {
        const data = this.dbData[this.getDataKey(categoryId)] || [];
        const filters = this.activeFilters[categoryId];
        
        const brands = [...new Set(data.map(item => item.brand || item.model_brand).filter(Boolean))];
        const types = this.getUniqueValues(data, this.getTypeField(categoryId));
        const prices = data.map(item => item.price_rub || item.price || 0).filter(p => p > 0);
        const minPrice = prices.length > 0 ? Math.min(...prices) : 0;
        const maxPrice = prices.length > 0 ? Math.max(...prices) : 1000000;
        
        return `
            <div class="filter-header">
                <h4>${this.categories.find(c => c.id === categoryId)?.icon} ${this.categories.find(c => c.id === categoryId)?.label}</h4>
                <button class="reset-filters-btn" data-category="${categoryId}">Сбросить</button>
            </div>
            
            <div class="filter-group">
                <label>🔍 Поиск</label>
                <input type="text" 
                       class="filter-search" 
                       data-category="${categoryId}" 
                       placeholder="Название, модель..." 
                       value="${filters.search}">
            </div>
            
            <div class="filter-group">
                <label>🏷️ Производитель</label>
                <select class="filter-brand" data-category="${categoryId}">
                    <option value="">Все производители</option>
                    ${brands.map(b => `<option value="${b}" ${filters.brand === b ? 'selected' : ''}>${b}</option>`).join('')}
                </select>
            </div>
            
            ${types.length > 0 ? `
            <div class="filter-group">
                <label>📊 Тип</label>
                <select class="filter-type" data-category="${categoryId}">
                    <option value="">Все типы</option>
                    ${types.map(t => `<option value="${t}" ${filters.type === t ? 'selected' : ''}>${t}</option>`).join('')}
                </select>
            </div>
            ` : ''}
            
            <div class="filter-group">
                <label>💰 Цена (₽)</label>
                <div class="price-range">
                    <input type="number" 
                           class="filter-price-min" 
                           data-category="${categoryId}" 
                           placeholder="От ${this.formatPrice(minPrice)}" 
                           value="${filters.priceMin}"
                           min="${minPrice}"
                           max="${maxPrice}">
                    <span>—</span>
                    <input type="number" 
                           class="filter-price-max" 
                           data-category="${categoryId}" 
                           placeholder="До ${this.formatPrice(maxPrice)}" 
                           value="${filters.priceMax}"
                           min="${minPrice}"
                           max="${maxPrice}">
                </div>
            </div>
            
            <div class="filter-stats">
                <div class="stat-item">
                    <span class="stat-label">Найдено:</span>
                    <span class="stat-value filter-count" data-category="${categoryId}">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Выбрано:</span>
                    <span class="stat-value selected-count" data-category="${categoryId}">0</span>
                </div>
            </div>
        `;
    }

    formatPrice(price) {
        return price.toLocaleString('ru-RU');
    }
    
    renderAllSections() {
        this.categories.forEach(cat => {
            this.renderSection(cat.id, cat.label, this.dbData[cat.dataKey]);
        });
        this.updateAllSectionsState();
        this.updateSidebarCounts();
    }

    updateSidebarCounts() {
        this.categories.forEach(cat => {
            const data = this.dbData[cat.dataKey] || [];
            const filtered = this.applyFilters(cat.id, data);
            const countEl = document.querySelector(`.nav-count[data-category="${cat.id}"]`);
            if (countEl) {
                countEl.textContent = filtered.length;
            }
            
            const filterCountEl = document.querySelector(`.filter-count[data-category="${cat.id}"]`);
            if (filterCountEl) {
                filterCountEl.textContent = filtered.length;
            }
            
            const selectedCount = Array.isArray(this.selection[cat.id]) 
                ? this.selection[cat.id].length 
                : (this.selection[cat.id] ? 1 : 0);
            const selectedCountEl = document.querySelector(`.selected-count[data-category="${cat.id}"]`);
            if (selectedCountEl) {
                selectedCountEl.textContent = selectedCount;
            }
        });
    }

    updateAllSectionsState() {
        this.categories.forEach(cat => {
            const dataKey = cat.dataKey;
            const allData = this.dbData[dataKey] || [];
            
            const filteredData = this.applyFilters(cat.id, allData);
            const { compatible, incompatible, selected } = this.filterDataByCompatibility(cat.id, filteredData);
            
            this.renderSectionList(cat.id, compatible, incompatible, selected, cat.multiSelect);
            this.updateSectionVisualState(cat.id);
        });
        
        this.updateTotalPrice();
        this.checkCompatibility();
        this.updateBuildSummary();
        this.updateSidebarCounts();
    }

    applyFilters(categoryId, data) {
        const filters = this.activeFilters[categoryId];
        if (!filters) return data;
        
        return data.filter(item => {
            if (!item) return false;
            
            if (filters.search) {
                const searchLower = filters.search.toLowerCase();
                const name = (item.model_name || item.name || '').toLowerCase();
                const brand = (item.brand || '').toLowerCase();
                if (!name.includes(searchLower) && !brand.includes(searchLower)) {
                    return false;
                }
            }
            
            if (filters.brand) {
                const itemBrand = item.brand || item.model_brand || '';
                if (itemBrand !== filters.brand) {
                    return false;
                }
            }
            
            const price = item.price_rub || item.price || 0;
            if (filters.priceMin && price < parseInt(filters.priceMin)) {
                return false;
            }
            if (filters.priceMax && price > parseInt(filters.priceMax)) {
                return false;
            }
            
            if (filters.type) {
                const typeField = this.getTypeField(categoryId);
                const itemType = item[typeField] || item.type || '';
                if (itemType !== filters.type) {
                    return false;
                }
            }
            
            return true;
        });
    }

    getTypeField(categoryId) {
        const typeFields = {
            'motherboard': 'form_factor',
            'cpu': 'socket_type',
            'ram': 'type',
            'gpu': 'interface',
            'storage': 'interface',
            'cooler': 'type',
            'psua': 'efficiency_rating',
            'case': 'form_factor'
        };
        return typeFields[categoryId] || 'type';
    }
    
    getUniqueValues(data, field) {
        return [...new Set(data.map(item => item[field]).filter(Boolean))];
    }

    checkCompatibilityForItem(item, category) {
        try {
            const testSelection = { ...this.selection, [category]: item };
            
            if (category !== 'motherboard' && !testSelection['motherboard']) {
                return { compatible: false, reason: 'Сначала выберите материнскую плату' };
            }

            const result = this.validator?.validateBuild?.(testSelection);
            
            if (!result || !result.details) {
                return { compatible: true, reason: null };
            }

            const categoryCheck = result.details.find(d => d?.category === this.getCategoryLabel(category));
            
            if (categoryCheck && categoryCheck.compatible === false) {
                return {
                    compatible: false,
                    reason: categoryCheck.errors?.[0] || 'Не совместим с текущей сборкой'
                };
            }

            if (category === 'cpu' && testSelection['motherboard']) {
                const mb = testSelection['motherboard'];
                if (item.socket_type && mb?.socket_type && item.socket_type !== mb.socket_type) {
                    return { compatible: false, reason: `Несовместимый сокет: нужен ${mb.socket_type}` };
                }
            }
            
            if (category === 'ram' && testSelection['motherboard']) {
                const mb = testSelection['motherboard'];
                if (item.type && mb?.ram_type && item.type !== mb.ram_type) {
                    return { compatible: false, reason: `Нужна память ${mb.ram_type}` };
                }
            }
            
            if (category === 'gpu' && testSelection['case']) {
                const case_ = testSelection['case'];
                if (item.length_mm && case_?.max_gpu_length_mm && item.length_mm > case_.max_gpu_length_mm) {
                    return { compatible: false, reason: `Не поместится в корпус (макс. ${case_.max_gpu_length_mm}мм)` };
                }
            }
            
            if (category === 'cooler' && testSelection['cpu']) {
                const cpu = testSelection['cpu'];
                if (item.supported_sockets && cpu?.socket_type && !item.supported_sockets.includes(cpu.socket_type)) {
                    return { compatible: false, reason: `Не поддерживает сокет ${cpu.socket_type}` };
                }
                if (item.max_tdp_watts && cpu?.tdp_watts && cpu.tdp_watts > item.max_tdp_watts) {
                    return { compatible: false, reason: `TDP процессора (${cpu.tdp_watts}W) превышает лимит кулера` };
                }
            }

            return { compatible: true, reason: null };
        } catch (error) {
            console.error('Ошибка проверки совместимости:', error);
            return { compatible: true, reason: null };
        }
    }

    checkMotherboardLimits(category, currentSelection) {
        const mb = this.selection['motherboard'];
        if (!mb) return { allowed: true, max: 99, current: 0 };
        
        let max = 99;
        let current = 0;
        
        if (category === 'ram') {
            max = mb.ram_slots_count || 4;
            current = Array.isArray(currentSelection) ? currentSelection.length : (currentSelection ? 1 : 0);
        } else if (category === 'storage') {
            const m2Slots = mb.m2_slots_count || 0;
            const sataPorts = mb.sata_ports_count || 0;
            max = m2Slots + sataPorts;
            
            const storageSelection = this.selection['storage'];
            if (Array.isArray(storageSelection)) {
                current = storageSelection.length;
            } else if (storageSelection) {
                current = 1;
            }
        } else if (category === 'gpu') {
            max = mb.pcie_slots_count || 1;
            current = currentSelection ? 1 : 0;
        }
        
        return {
            allowed: current < max,
            max: max,
            current: current,
            remaining: max - current
        };
    }

    filterDataByCompatibility(categoryId, data) {
        const compatible = [];
        const incompatible = [];
        const selected = [];
        
        if (!Array.isArray(data)) {
            return { compatible: [], incompatible: [], selected: [] };
        }
        
        const currentSelection = this.selection[categoryId];
        const isSelectedArray = Array.isArray(currentSelection);
        
        data.forEach(item => {
            if (!item) return;
            
            const isSelected = isSelectedArray 
                ? currentSelection.some(s => s?.id === item.id)
                : currentSelection?.id === item.id;
            
            if (isSelected) {
                selected.push({ ...item, _compatibility: { compatible: true } });
                return;
            }
            
            if (this.isMultiSelectCategory(categoryId)) {
                const limits = this.checkMotherboardLimits(categoryId, currentSelection);
                if (!limits.allowed) {
                    incompatible.push({ 
                        ...item, 
                        _compatibility: { 
                            compatible: false, 
                            reason: `Достигнут лимит: ${limits.current}/${limits.max} слотов` 
                        } 
                    });
                    return;
                }
            }
            
            const check = this.checkCompatibilityForItem(item, categoryId);
            
            if (check.compatible) {
                compatible.push({ ...item, _compatibility: check });
            } else {
                incompatible.push({ ...item, _compatibility: check });
            }
        });
        
        return { compatible, incompatible, selected };
    }
    
    isMultiSelectCategory(categoryId) {
        const cat = this.categories.find(c => c.id === categoryId);
        return cat?.multiSelect || false;
    }
    
    renderSection(id, label, data) {
        let container = document.getElementById(`${id}List`);
        if (!container) return;
        this.renderSectionList(id, [], [], [], false);
        this.updateSectionVisualState(id);
    }

    renderSectionList(id, compatibleData, incompatibleData, selectedData, isMultiSelect) {
        const container = document.getElementById(`${id}List`);
        if (!container) return;
        
        if (!Array.isArray(compatibleData)) compatibleData = [];
        if (!Array.isArray(incompatibleData)) incompatibleData = [];
        if (!Array.isArray(selectedData)) selectedData = [];
        
        const totalItems = compatibleData.length + incompatibleData.length + selectedData.length;
        
        if (totalItems === 0) {
            const motherboard = this.selection['motherboard'];
            let msg = 'Компоненты не найдены';
            if (!motherboard && id !== 'motherboard') {
                msg = '🔒 Выберите материнскую плату, чтобы увидеть совместимые компоненты';
            }
            container.innerHTML = `<div class="no-items">${msg}</div>`;
            return;
        }
        
        let html = '';
        
        if (selectedData.length > 0) {
            html += `<div class="section-group selected"><h4>⭐ Выбрано (${selectedData.length})</h4><div class="cards-grid">`;
            selectedData.forEach(item => {
                html += this.createComponentCardHTML(item, id, true, true, isMultiSelect);
            });
            html += `</div></div>`;
        }
        
        if (compatibleData.length > 0) {
            html += `<div class="section-group compatible"><h4>✅ Совместимые (${compatibleData.length})</h4><div class="cards-grid">`;
            compatibleData.forEach(item => {
                html += this.createComponentCardHTML(item, id, true, false, isMultiSelect);
            });
            html += `</div></div>`;
        }
        
        if (incompatibleData.length > 0) {
            html += `<div class="section-group incompatible"><h4>⚠️ Не совместимы (${incompatibleData.length})</h4><div class="cards-grid">`;
            incompatibleData.forEach(item => {
                html += this.createComponentCardHTML(item, id, false, false, isMultiSelect, item._compatibility?.reason);
            });
            html += `</div></div>`;
        }
        
        container.innerHTML = html;
        
        container.querySelectorAll('.component-card:not(.incompatible)').forEach(card => {
            card.addEventListener('click', (e) => {
                if (e.target.closest('.remove-btn')) return;
                
                const item = (this.dbData[this.getDataKey(id)] || []).find(i => i?.id === card.dataset.id);
                if (item) this.handleComponentClick(id, item, isMultiSelect);
            });
        });
        
        container.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const itemId = btn.dataset.itemId;
                this.removeComponent(id, itemId, isMultiSelect);
            });
        });
    }
    
    createComponentCardHTML(item, category, isCompatible, isSelected, isMultiSelect, incompatibilityReason = null) {
        const specs = this.extractSpecs(item, category);
        let compatClass = isSelected ? 'selected' : (isCompatible ? 'compatible' : 'incompatible');
        const lockIcon = isCompatible || isSelected ? '' : '🔒 ';
        const reasonAttr = incompatibilityReason ? `title="${this.escapeHtml(incompatibilityReason)}"` : '';
        
        return `
            <div class="component-card ${compatClass}" 
                 data-id="${item.id}" 
                 data-category="${category}"
                 ${reasonAttr}
                 style="${!isCompatible && !isSelected ? 'opacity: 0.6; cursor: not-allowed;' : ''}">
                <div class="card-header">
                    <strong class="component-name">${lockIcon}${specs.name}</strong>
                    <span class="component-brand">${specs.brand || ''}</span>
                    ${isSelected ? '<span class="selected-badge">✓</span>' : ''}
                </div>
                <div class="component-specs">${specs.text}</div>
                <div class="component-price">${specs.price} ₽</div>
                ${isSelected ? `
                    <button class="remove-btn" data-item-id="${item.id}" title="Удалить из сборки">
                        🗑️ Удалить
                    </button>
                ` : ''}
                ${!isCompatible && !isSelected && incompatibilityReason ? 
                    `<div class="compatibility-reason">⚠️ ${this.escapeHtml(incompatibilityReason)}</div>` : ''}
                ${isMultiSelect && !isSelected ? `
                    <div class="multi-select-hint">+ Добавить</div>
                ` : ''}
            </div>
        `;
    }
    
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    extractSpecs(item, category) {
        let name = '', brand = '', text = '';
        let price = item?.price_rub || item?.price || 'Не указана';
        
        switch(category) {
            case 'cpu':
                brand = item?.model_name || '';
                text = `${item?.socket_type || ''} • TDP: ${item?.tdp_watts || 'N/A'}Вт`;
                break;
            case 'motherboard':
                brand = item?.model_name || '';
                text = `${item?.chipset || ''} • Socket: ${item?.socket_type || ''} • RAM: ${item?.ram_slots_count || '?'} слота`;
                break;
            case 'ram':
                brand = item?.model_name || '';
                text = `${item?.type || ''} • ${item?.speed_mhz || 0}MHz • ${item?.capacity_gb || ''}GB`;
                break;
            case 'gpu':
                brand = item?.model_name || '';
                text = `${item?.memory_size_gb || 0}ГБ • ${item?.interface || ''} • ${item?.length_mm || '?'}мм`;
                break;
            case 'storage':
                brand = item?.model_name || '';
                text = `${item?.type || ''} • ${item?.interface || ''} • ${item?.capacity_gb || item?.read_speed_mbps || 0}`;
                break;
            case 'cooler':
                brand = item?.model_name || '';
                text = `${item?.type || ''} • TDP: ${item?.max_tdp_watts || '?'}W • ${item?.height_mm || '?'}мм`;
                break;
            case 'psua':
                brand = item?.model_name || '';
                text = `${item?.total_wattage_watts || ''}W • ${item?.efficiency_rating || ''}`;
                break;
            case 'case':
                brand = item?.model_name || '';
                text = `${item?.form_factor || ''} • GPU: ${item?.max_gpu_length_mm || '?'}мм • CPU: ${item?.max_cooler_height_mm || '?'}мм`;
                break;
            default:
                name = item?.model_name || item?.name || 'Компонент';
        }
        
        if (!name && brand) name = brand;
        
        return { name: name || 'Компонент', brand, text, price };
    }
    
    handleComponentClick(category, item, isMultiSelect) {
        const check = this.checkCompatibilityForItem(item, category);
        if (!check.compatible) {
            alert(`❌ Нельзя выбрать:\n${check.reason}`);
            return;
        }

        const limits = this.checkMotherboardLimits(category, this.selection[category]);
        if (isMultiSelect && !limits.allowed) {
            alert(`⚠️ Достигнут лимит слотов: ${limits.current}/${limits.max}\nУдалите один компонент или выберите материнскую плату с большим количеством слотов`);
            return;
        }

        const currentSelection = this.selection[category];
        
        if (isMultiSelect) {
            if (!Array.isArray(currentSelection)) {
                this.selection[category] = [];
            }
            
            const alreadySelected = this.selection[category].some(s => s?.id === item.id);
            if (alreadySelected) {
                return;
            }
            
            this.selection[category].push(item);
        } else {
            if (currentSelection && currentSelection.id === item.id) {
                this.deselectCategory(category);
                return;
            }
            
            this.selection[category] = item;
        }
        
        this.updateAllSectionsState();
        this.updateUIForCategory(category);
    }
    
    removeComponent(category, itemId, isMultiSelect) {
        if (isMultiSelect) {
            const currentSelection = this.selection[category];
            if (Array.isArray(currentSelection)) {
                this.selection[category] = currentSelection.filter(item => item?.id !== itemId);
                if (this.selection[category].length === 0) {
                    this.selection[category] = null;
                }
            }
        } else {
            this.selection[category] = null;
        }
        
        this.updateAllSectionsState();
        this.updateUIForCategory(category);
    }
    
    getDataKey(category) {
        const map = {
            'cpu': 'cpu',
            'motherboard': 'motherboard',
            'ram': 'ram',
            'gpu': 'graphicsCard',
            'storage': 'storage',
            'cooler': 'cooler',
            'psua': 'powerSupply',
            'case': 'case'
        };
        return map[category] || category;
    }
    
    getCategoryLabel(category) {
        const cat = this.categories.find(c => c.id === category);
        return cat?.label || category;
    }
    
    updateUIForCategory(category) {
        document.querySelectorAll(`[data-category="${category}"]`).forEach(card => {
            const isSelected = Array.isArray(this.selection[category])
                ? this.selection[category].some(s => s?.id === card.dataset.id)
                : this.selection[category]?.id === card.dataset.id;
            
            if (isSelected) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
        });
        
        document.querySelectorAll('.nav-item').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${category}`) {
                link.classList.add('active');
            }
        });
    }
    
    updateSectionVisualState(categoryId) {
        const container = document.getElementById(`${categoryId}List`);
        const header = document.querySelector(`[data-section-header="${categoryId}"]`) || 
                       document.getElementById(`${categoryId}Header`);
        
        const motherboard = this.selection['motherboard'];
        const isLocked = !motherboard && categoryId !== 'motherboard';

        if (isLocked) {
            if (container) container.classList.add('section-locked');
            if (header) {
                header.classList.add('locked');
                header.title = 'Сначала выберите материнскую плату';
            }
        } else {
            if (container) container.classList.remove('section-locked');
            if (header) {
                header.classList.remove('locked');
                header.title = '';
            }
        }
    }
    
    deselectCategory(category) {
        this.selection[category] = null;
        this.updateAllSectionsState();
        this.updateUIForCategory(category);
    }

    updateFilter(categoryId, filterType, value) {
        if (!this.activeFilters[categoryId]) {
            this.activeFilters[categoryId] = {};
        }
        this.activeFilters[categoryId][filterType] = value;
        this.updateAllSectionsState();
    }

    resetCategoryFilters(categoryId) {
        this.activeFilters[categoryId] = {
            search: '',
            brand: '',
            priceMin: '',
            priceMax: '',
            type: '',
            additional: {}
        };
        
        const filterPanel = document.getElementById(`filterPanel-${categoryId}`);
        if (filterPanel) {
            filterPanel.querySelector('.filter-search').value = '';
            filterPanel.querySelector('.filter-brand').value = '';
            const typeSelect = filterPanel.querySelector('.filter-type');
            if (typeSelect) typeSelect.value = '';
            filterPanel.querySelector('.filter-price-min').value = '';
            filterPanel.querySelector('.filter-price-max').value = '';
        }
        
        this.updateAllSectionsState();
    }

    resetAllFilters() {
        this.initializeFilters();
        this.renderSidebar();
        this.updateAllSectionsState();
    }

    switchFilterCategory(categoryId) {
        this.activeCategoryFilter = categoryId;
        
        // Обновляем навигацию
        document.querySelectorAll('.filter-nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.category === categoryId);
        });
        
        // Обновляем панели фильтров
        document.querySelectorAll('.filter-panel').forEach(panel => {
            panel.classList.toggle('active', panel.dataset.category === categoryId);
        });
    }
    
    setupEventListeners() {
        // Навигация фильтров
        document.querySelectorAll('.filter-nav-item').forEach(item => {
            item.addEventListener('click', () => {
                this.switchFilterCategory(item.dataset.category);
            });
        });
        
        // Обработчики фильтров
        this.categories.forEach(cat => {
            const filterPanel = document.getElementById(`filterPanel-${cat.id}`);
            if (!filterPanel) return;
            
            const searchInput = filterPanel.querySelector('.filter-search');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    clearTimeout(this.searchTimeouts[cat.id]);
                    this.searchTimeouts[cat.id] = setTimeout(() => {
                        this.updateFilter(cat.id, 'search', e.target.value.trim());
                    }, 300);
                });
            }
            
            const brandSelect = filterPanel.querySelector('.filter-brand');
            if (brandSelect) {
                brandSelect.addEventListener('change', (e) => {
                    this.updateFilter(cat.id, 'brand', e.target.value);
                });
            }
            
            const typeSelect = filterPanel.querySelector('.filter-type');
            if (typeSelect) {
                typeSelect.addEventListener('change', (e) => {
                    this.updateFilter(cat.id, 'type', e.target.value);
                });
            }
            
            const priceMinInput = filterPanel.querySelector('.filter-price-min');
            if (priceMinInput) {
                priceMinInput.addEventListener('input', (e) => {
                    this.updateFilter(cat.id, 'priceMin', e.target.value);
                });
            }
            
            const priceMaxInput = filterPanel.querySelector('.filter-price-max');
            if (priceMaxInput) {
                priceMaxInput.addEventListener('input', (e) => {
                    this.updateFilter(cat.id, 'priceMax', e.target.value);
                });
            }
            
            const resetBtn = filterPanel.querySelector('.reset-filters-btn');
            if (resetBtn) {
                resetBtn.addEventListener('click', () => {
                    this.resetCategoryFilters(cat.id);
                });
            }
        });
        
        // Сброс всех фильтров
        const resetAllBtn = document.getElementById('resetAllFilters');
        if (resetAllBtn) {
            resetAllBtn.addEventListener('click', () => {
                this.resetAllFilters();
            });
        }
        
        // Закрытие sidebar на мобильных
        const closeSidebarBtn = document.getElementById('closeSidebar');
        if (closeSidebarBtn) {
            closeSidebarBtn.addEventListener('click', () => {
                document.getElementById('filterSidebar').classList.remove('open');
            });
        }
        
        // Кнопка сброса сборки
        const resetBtn = document.getElementById('resetBuild');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetBuild());
        }
        
        // Кнопка открытия sidebar на мобильных
        const openSidebarBtn = document.getElementById('openSidebar');
        if (openSidebarBtn) {
            openSidebarBtn.addEventListener('click', () => {
                document.getElementById('filterSidebar').classList.add('open');
            });
        }
    }
    
    updateTotalPrice() {
        let total = 0;
        Object.values(this.selection).forEach(item => {
            if (Array.isArray(item)) {
                item.forEach(i => {
                    if (i) total += i.price_rub || i.price || 0;
                });
            } else if (item) {
                total += item.price_rub || item.price || 0;
            }
        });
        
        const element = document.getElementById('totalPrice');
        if (element) {
            element.textContent = total.toLocaleString('ru-RU', {style: 'currency', currency: 'RUB'}).replace('RUB ', '') + ' ₽';
        }
    }
    
    checkCompatibility() {
        const statusEl = document.getElementById('compatibilityStatus');
        const reportEl = document.getElementById('reportDetails');
        
        if (!statusEl || !reportEl) return;
        
        if (!this.selection['motherboard']) {
            statusEl.innerHTML = `<span style="color: var(--text-secondary)">⏳ Выберите материнскую плату для проверки совместимости...</span>`;
            reportEl.innerHTML = '';
            return;
        }

        try {
            const validationResult = this.validator?.validateBuild?.(this.selection);
            
            if (!validationResult) {
                statusEl.innerHTML = `<span style="color: var(--text-secondary)">ℹ️ Проверка совместимости недоступна</span>`;
                reportEl.innerHTML = '<div class="report-item">Данные валидации не получены</div>';
                return;
            }

            const isCompatible = validationResult.overall_compatible === true;
            const score = validationResult.overall_score ?? 0;
            
            if (isCompatible) {
                statusEl.innerHTML = `<span style="color: var(--success)">✔️ Сборка совместима! Оценка: ${Math.round(score)}/100</span>`;
            } else {
                const errorCount = validationResult.details?.filter?.(d => d?.errors?.length > 0).length || 0;
                statusEl.innerHTML = `<span style="color: var(--error)">✖️ Найдено проблем: ${errorCount}</span>`;
            }
            
            this.showCompatibilityReport(validationResult);
        } catch (error) {
            console.error('❌ Ошибка checkCompatibility:', error);
            statusEl.innerHTML = `<span style="color: var(--error)">⚠️ Ошибка проверки</span>`;
            reportEl.innerHTML = '';
        }
    }
    
    showCompatibilityReport(report) {
        const container = document.getElementById('reportDetails');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (!report || !Array.isArray(report.details)) {
            container.innerHTML = '<div class="report-item">Нет данных для отображения</div>';
            return;
        }

        report.details.forEach(item => {
            if (!item) return;
            
            const div = document.createElement('div');
            const isError = Array.isArray(item.errors) && item.errors.length > 0;
            const isWarning = Array.isArray(item.warnings) && item.warnings.length > 0;
            
            const score = item.score ?? item.points ?? 100;
            
            div.className = `report-item ${isError ? 'error' : (isWarning ? 'warning' : 'success')}`;
            
            let html = `<strong>${item.category || 'Компонент'}</strong> (${score}/100)<br>`;
            
            if (item.errors) {
                item.errors.forEach(err => {
                    html += `<div style="margin-left: 20px; color: var(--error)">• ❌ ${this.escapeHtml(err)}</div>`;
                });
            }
            
            if (item.warnings) {
                item.warnings.forEach(warn => {
                    html += `<div style="margin-left: 20px; color: var(--warning)">• ⚠️ ${this.escapeHtml(warn)}</div>`;
                });
            }
            
            div.innerHTML = html;
            container.appendChild(div);
        });
    }
    
    updateBuildSummary() {
        const list = document.getElementById('buildList');
        if (!list) return;
        
        list.innerHTML = '';
        
        this.categories.forEach(cat => {
            const item = this.selection[cat.id];
            if (!item) return;
            
            if (Array.isArray(item)) {
                item.forEach((subItem, index) => {
                    if (!subItem) return;
                    
                    const li = document.createElement('li');
                    let displayText = subItem.name || subItem.model_name?.split(' ')[0] || subItem.id || 'Выбрано';
                    if (subItem.brand && !displayText.includes(subItem.brand)) displayText += ` ${subItem.brand}`;
                    if (subItem.price_rub) displayText += ` • ${subItem.price_rub} ₽`;
                    
                    li.innerHTML = `<strong>${cat.label} #${index + 1}:</strong> ${this.escapeHtml(displayText)} 
                        <button class="remove-summary-btn" data-category="${cat.id}" data-index="${index}">✕</button>`;
                    li.style.padding = '0.5rem';
                    li.style.borderBottom = '1px solid var(--border-color)';
                    li.style.display = 'flex';
                    li.style.justifyContent = 'space-between';
                    li.style.alignItems = 'center';
                    
                    list.appendChild(li);
                });
            } else {
                const li = document.createElement('li');
                let displayText = item.name || item.model_name?.split(' ')[0] || item.id || 'Выбрано';
                if (item.brand && !displayText.includes(item.brand)) displayText += ` ${item.brand}`;
                if (item.price_rub) displayText += ` • ${item.price_rub} ₽`;
                
                li.innerHTML = `<strong>${cat.label}:</strong> ${this.escapeHtml(displayText)} 
                    <button class="remove-summary-btn" data-category="${cat.id}">✕</button>`;
                li.style.padding = '0.5rem';
                li.style.borderBottom = '1px solid var(--border-color)';
                li.style.display = 'flex';
                li.style.justifyContent = 'space-between';
                li.style.alignItems = 'center';
                li.style.cursor = 'pointer';
                li.title = "Нажмите, чтобы снять выбор";
                li.onclick = (e) => {
                    if (!e.target.closest('.remove-summary-btn')) {
                        this.deselectCategory(cat.id);
                    }
                };
                
                list.appendChild(li);
            }
        });
        
        list.querySelectorAll('.remove-summary-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const category = btn.dataset.category;
                const index = btn.dataset.index;
                const isMultiSelect = this.isMultiSelectCategory(category);
                
                if (isMultiSelect && index !== undefined) {
                    const currentSelection = this.selection[category];
                    if (Array.isArray(currentSelection)) {
                        currentSelection.splice(index, 1);
                        if (currentSelection.length === 0) {
                            this.selection[category] = null;
                        }
                    }
                } else {
                    this.selection[category] = null;
                }
                
                this.updateAllSectionsState();
            });
        });
        
        if (list.children.length === 0) {
            list.innerHTML = '<li style="text-align: center; color: var(--text-secondary); padding: 1rem;">🖥️ Нет выбранных компонентов.<br>Начните с выбора материнской платы.</li>';
        }
    }
    
    resetBuild() {
        Object.keys(this.selection).forEach(key => {
            this.selection[key] = null;
        });
        
        this.initializeFilters();
        
        this.categories.forEach(cat => {
            const input = document.getElementById(`${cat.id}Search`);
            if (input) {
                input.value = '';
                input.disabled = (cat.id !== 'motherboard');
                input.placeholder = cat.id !== 'motherboard' ? "🔒 Сначала выберите материнскую плату" : "Поиск...";
                
                clearTimeout(this.searchTimeouts[cat.id]);
            }
            
            this.resetCategoryFilters(cat.id);
        });
        
        document.querySelectorAll('.component-card.selected').forEach(card => {
            card.classList.remove('selected');
        });
        
        this.updateAllSectionsState();
        
        document.querySelectorAll('.nav-item').forEach(link => {
            link.classList.remove('active');
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new ConfiguratorApp();
});