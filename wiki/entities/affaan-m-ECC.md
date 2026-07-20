# affaan-m/ECC

> tags: #ECC #EllipticCurveCryptography #Cryptography #Python
> source: [affaan-m/ECC](https://github.com/affaan-m/ECC)
> score: 技术深度7/10 | 实用价值7/10 | 时效性7/10 | 领域匹配8/10 | 综合 7.0/10

## 核心概念
ECC（椭圆曲线密码学）教育性实现项目，提供椭圆曲线数学运算与基础加密原语的Python实现。核心涵盖有限域上的点加、点乘运算，以及基于ECC的密钥交换（ECDH）和数字签名（ECDSA）算法。

## 设计原理
基于有限域Fp上的椭圆曲线群运算：曲线方程 y² = x³ + ax + b (mod p)，利用群的加法封闭性与离散对数难题（ECDLP）构建密码学安全。点乘通过double-and-add算法实现，复杂度O(log n)。

## 关键实现
典型实现包含：曲线参数类（a, b, p, G, n）；Point类实现__add__、__rmul__等运算符重载；modular_inverse采用扩展欧几里得算法；ECDH通过双方各自生成私钥d并计算d*G得到共享密钥；ECDSA签名涉及k选取、r=(kG).x mod n、s=k⁻¹(z+rd) mod n。常见曲线支持secp256k1、secp256r1。

## 关联分析
同类项目对比：tlsfuzzer/ecdsa（测试套件）、ofek/pyca/cryptography（生产级库）、bitcoin-core/secp256k1（C高性能实现）、libressl（OpenSSL分支）。本项目定位为教学参考，非生产可用。

## 可执行建议
1) 克隆仓库运行示例脚本，对比secp256k1与secp256r1的运算结果差异；2) 尝试修改曲线参数观察非法a/b值导致的奇点退化（如4a³+27b²≡0 mod p时曲线不可逆）。
