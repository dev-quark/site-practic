class DatabaseLoader {
    constructor(basePath = './data') {
        this.basePath = basePath;
        this.data = {};
        this.allComponentsCache = []; // Для быстрого поиска
    }
    
    async loadAll() {
        const files = {
            cpu: 'cpu.json',
            motherboard: 'motherboard.json',
            ram: 'OZU.json',
            graphicsCard: 'video_card.json',
            storage: 'PZU.json',
            cooler: 'Cooler.json',
            powerSupply: 'PowerCub.json',
            case: 'frame.json'
        };
        
        for (const [key, filename] of Object.entries(files)) {
            try {
                const response = await fetch(`${this.basePath}/${filename}`);
                if (!response.ok) throw new Error(`Файл ${filename} не найден`);
                
                const content = await response.json();
                this.data[key] = Array.isArray(content) ? content : [content];
                
                // Добавляем в кэш для поиска
                this.addComponentsToSearch(key, this.data[key]);
                
                console.log(`✅ Загружено: ${filename} (${this.data[key].length} шт.)`);
            } catch (error) {
                console.warn(`⚠️ Ошибка загрузки ${filename}:`, error.message);
                this.data[key] = [];
            }
        }
        
        return this.data;
    }
    
    addComponentsToSearch(category, items) {
        items.forEach(item => {
            this.allComponentsCache.push({
                ...item,
                category: category
            });
        });
    }
    
    getComponent(type, id) {
        const collection = this.data[type] || [];
        return collection.find(item => item.id === id);
    }
    
    getAllData() {
        return this.data;
    }
    
    searchByCategoryAndQuery(category, query) {
        const collection = this.data[category.toLowerCase()] || [];
        const q = query.toLowerCase().trim();
        
        if (!q) return collection;
        
        return collection.filter(item => {
            // Поиск по многим полям одновременно
            const name = item.model_name || '';
            const brand = item.brand || '';
            const description = item.description || '';
            
            const textToSearch = `${name} ${brand} ${description}`.toLowerCase();
            
            return textToSearch.includes(q);
        });
    }
}

// Инициализация загрузчика
const dbLoader = new DatabaseLoader('./data');
window.dbLoader = dbLoader;