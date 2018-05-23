#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

int main() {
    static std::mutex mtx;
    static std::vector<std::thread> thrs;
    while ( true ) {
        {
            std::lock_guard<std::mutex> lck(mtx);
            std::cerr << std::this_thread::get_id() << std::endl;
            thrs.emplace_back(main);
            std::cerr << thrs.size() << std::endl;
        }
    }
    return 0;
}
